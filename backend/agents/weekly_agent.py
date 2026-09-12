"""
Weekly SEO analysis agent.

Generates a bounded SEO analysis using:
- Google Search Console data
- Website content
- The staged SEO skill instructions
- Historical SEO report summaries

Historical reports are exposed to the agent through a database tool.
Only summaries are returned to the LLM, with a hard result limit.
"""

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

from strands import Agent
from strands.models.litellm import LiteLLMModel

from core.config import settings
from tools.search_console_tool import collect_search_console_data
from tools.user_context_tool import create_user_context_tool
from tools.website_tool import scrape_website
from tools.historical_reports_tool import create_historical_reports_tool
from services.seo_reports_service import SEOReportsService


logger = logging.getLogger(__name__)


# The skill lives in backend/system-prompt/SKILL.md. This used to point at
# backend/skills/staged-seo-growth-agent/, which does not exist, so the loader
# fell back to "no skill available" and the 9-stage framework never reached
# the model.
SKILLS_PATH = (
    Path(__file__).resolve().parent.parent
    / "system-prompt"
    / "SKILL.md"
)

# ---------------------------------------------------------------------
# Prompt-size bounds
# ---------------------------------------------------------------------
# These are driven by the provider's tokens-per-minute ceiling, not by the
# model's context window. gpt-oss-120b on Groq has a 131k context but the
# free tier only allows ~8,000 tokens per minute, counting prompt and
# completion together. Exceeding it returns 429 regardless of how much
# context the model could technically accept.
#
# At roughly 4 characters per token, the demo profile below targets about
# 4,500 prompt tokens plus 2,500 output tokens, leaving headroom under
# 8,000 for a single request.
#
# Set SEO_DEMO_MODE=false in .env to restore the generous profile once the
# provider account has a higher allowance.

# Measured, not guessed. Groq rejected an 11,535 char prompt as 7,139 tokens,
# which is ~1.6 chars per token. URLs, dense JSON punctuation, and non-ASCII
# characters in scraped copy all tokenize far worse than prose, so the usual
# 4-chars-per-token rule of thumb is dangerously optimistic here.
CHARS_PER_TOKEN = 1.6

# The provider's hard per-minute ceiling for this model and tier.
TPM_LIMIT = 8_000

# Headroom for things outside the prompt string: the Strands system prompt,
# tool schemas, and tokenizer variance. Sites whose copy is not mostly English
# tokenize considerably worse per character, so this margin is what keeps a
# different property from tipping the request over the limit.
SAFETY_TOKENS = 1_400

if settings.SEO_DEMO_MODE:
    # Reasoning tokens are billed as output, so the reasoning budget and the
    # report share this allowance.
    MAX_OUTPUT_TOKENS = 3_000
    MAX_SKILL_CHARS = 1_600
    MAX_SNAPSHOT_CHARS = 1_400
    MAX_SNAPSHOT_LIST_ITEMS = 5
    MAX_PAGES = 5
    MAX_FIELD_CHARS = 90
    # Each tool call re-sends the entire prompt on the next turn, which
    # doubles token spend and breaks the per-minute budget. Historical
    # context is still supplied inline as a summary, so the agent keeps its
    # cross-run memory; it just cannot fetch more on demand.
    ENABLE_HISTORICAL_TOOL = False
else:
    MAX_OUTPUT_TOKENS = 8_192
    MAX_SKILL_CHARS = 20_000
    MAX_SNAPSHOT_CHARS = 15_000
    MAX_SNAPSHOT_LIST_ITEMS = 50
    MAX_PAGES = 150
    MAX_FIELD_CHARS = 1_000
    ENABLE_HISTORICAL_TOOL = True


# Everything the prompt string may occupy, derived from the limits above.
MAX_PROMPT_CHARS = int(
    (TPM_LIMIT - SAFETY_TOKENS - MAX_OUTPUT_TOKENS) * CHARS_PER_TOKEN
)


def _clip(text: str, limit: int, label: str) -> str:
    """Trim text to a character limit, preferring the last line boundary."""

    if len(text) <= limit:
        return text

    window = text[:limit]
    cut = window.rfind("\n")

    # Only honour the line boundary if it is not throwing away too much.
    if cut < limit * 0.6:
        cut = limit

    logger.warning(
        "Trimmed %s from %d to %d chars to stay inside the token budget",
        label,
        len(text),
        cut,
    )

    return window[:cut] + f"\n... ({label} truncated for token budget)"


def _enforce_prompt_budget(prompt: str) -> str:
    """Last-resort guard so a prompt can never exceed the provider's ceiling.

    Cuts from the middle, where the Search Console and page data sit. The head
    holds the skill and framing, the tail holds the output contract, and losing
    either produces a malformed report rather than a shallower one.
    """

    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    marker = "\n\n... (evidence truncated to fit the provider token budget)\n\n"
    keep = MAX_PROMPT_CHARS - len(marker)
    head = int(keep * 0.55)
    tail = keep - head

    logger.warning(
        "Prompt %d chars exceeded the %d char ceiling; cut %d chars from the "
        "middle. Analysis depth is reduced for this run.",
        len(prompt),
        MAX_PROMPT_CHARS,
        len(prompt) - MAX_PROMPT_CHARS,
    )

    return prompt[:head] + marker + prompt[-tail:]

# Distinct terminal signals so callers can tell success from failure
# instead of both paths ending in the same "Completed." string.
STATUS_COMPLETED = "Completed."
STATUS_FAILED = "Failed."


class WeeklyAgent:
    """
    Weekly SEO analysis agent.

    The agent receives current Search Console and website data and can
    optionally query previous SEO report summaries to understand historical
    context before generating the current analysis.
    """

    def __init__(self, db):

        logger.info("=" * 100)
        logger.info("INITIALIZING WEEKLY AGENT")
        logger.info("=" * 100)

        self.db = db

        # ---------------------------------------------------------
        # User context tool
        # ---------------------------------------------------------

        logger.info("Creating user context tool")

        self.user_tool = create_user_context_tool(db)

        # ---------------------------------------------------------
        # Historical reports
        # ---------------------------------------------------------

        logger.info("Creating historical SEO reports tool")

        self.historical_reports_tool = (
            create_historical_reports_tool(db)
        )

        # Service is responsible for persistence.
        self.seo_reports_service = SEOReportsService(db)

        # ---------------------------------------------------------
        # Load SEO skill
        # ---------------------------------------------------------

        self.skills_content = _clip(
            self._load_skills(),
            MAX_SKILL_CHARS,
            "SEO skill",
        )

        # ---------------------------------------------------------
        # LLM
        # ---------------------------------------------------------

        logger.info("Initializing LLM: %s", settings.LLM_MODEL_ID)

        self.model = LiteLLMModel(
            model_id=settings.LLM_MODEL_ID,
            client_args={
                "api_key": settings.LLM_API_KEY,
            },
            params={
                "temperature": 0,
                # Covers reasoning and the report together: on this model
                # reasoning tokens are billed as output, so they share the
                # same allowance.
                "max_tokens": MAX_OUTPUT_TOKENS,
                # "low" leaves more of that allowance for the report itself
                # rather than the private chain of thought, which matters when
                # the entire request has to fit inside 8k tokens per minute.
                "reasoning_effort": (
                    "low" if settings.SEO_DEMO_MODE else "medium"
                ),
            },
        )

        logger.info(
            "Weekly agent initialized successfully"
        )

        logger.info("=" * 100)

    # =================================================================
    # SKILLS
    # =================================================================

    @staticmethod
    def _load_skills() -> str:
        """
        Load the staged SEO skill instructions from SKILL.md.
        """

        logger.info(
            "Loading SEO skill from %s",
            SKILLS_PATH,
        )

        try:
            content = SKILLS_PATH.read_text(
                encoding="utf-8"
            )

            logger.info(
                "SEO skill loaded successfully (%d characters)",
                len(content),
            )

            return content

        except FileNotFoundError:

            logger.error(
                "SEO skill file not found: %s",
                SKILLS_PATH,
            )

            return (
                "No external SEO skill file was available. "
                "Follow the analysis instructions provided in the prompt."
            )

        except Exception:

            logger.exception(
                "Failed to load SEO skill"
            )

            return (
                "SEO skill could not be loaded. "
                "Follow the analysis instructions provided in the prompt."
            )

    # =================================================================
    # SITEMAP RESOLUTION
    # =================================================================

    @staticmethod
    def _resolve_sitemap_url(
        snapshot: dict,
        site_url: str,
    ) -> str | None:

        if not isinstance(snapshot, dict):
            logger.error(
                "Sitemap resolution failed: snapshot is not a dict"
            )
            return None

        sitemaps_data = snapshot.get("sitemaps")

        if isinstance(sitemaps_data, dict):
            sitemap_entries = sitemaps_data.get("sitemap")

        elif isinstance(sitemaps_data, list):
            sitemap_entries = sitemaps_data

        else:
            sitemap_entries = []

        if not sitemap_entries:
            sitemap_entries = []

        if not isinstance(sitemap_entries, list):
            sitemap_entries = []

        for entry in sitemap_entries:

            if not isinstance(entry, dict):
                continue

            path = entry.get("path")

            if path:
                logger.info(
                    "Search Console sitemap found: %s",
                    path,
                )
                return path

        # Fallback
        if site_url.startswith(("http://", "https://")):

            fallback = urljoin(
                site_url,
                "/sitemap.xml",
            )

            logger.warning(
                "No submitted sitemap found. Using fallback: %s",
                fallback,
            )

            return fallback

        return None

    # =================================================================
    # WEBSITE SCRAPER
    # =================================================================

    async def _scrape_pages(
        self,
        sitemap_url: str | None,
    ) -> list[dict]:

        if sitemap_url is None:

            logger.warning(
                "No sitemap available. Skipping website scraping."
            )

            return []

        started = time.perf_counter()

        try:

            result = await scrape_website(
                sitemap_url=sitemap_url,
            )

            elapsed = time.perf_counter() - started

            logger.info(
                "Website scraping completed in %.2fs",
                elapsed,
            )

            if isinstance(result, list):

                logger.info(
                    "Scraped %d pages",
                    len(result),
                )

                return result

            logger.warning(
                "Scraper returned unexpected type: %s",
                type(result).__name__,
            )

            return []

        except Exception:

            elapsed = time.perf_counter() - started

            logger.exception(
                "Website scraping failed after %.2fs",
                elapsed,
            )

            # Search Console analysis can still continue.
            return []

    # =================================================================
    # PROMPT INPUT BOUNDING
    # =================================================================

    @staticmethod
    def _truncate_snapshot(obj, max_items: int = MAX_SNAPSHOT_LIST_ITEMS):
        """
        Recursively cap list lengths inside the Search Console snapshot,
        without assuming its exact schema (queries/pages/dates rows etc).
        Cheap insurance against an unusually query-diverse property; not
        needed at current small-medium site volumes but avoids silent
        context blowup if that ever changes.
        """

        if isinstance(obj, dict):
            return {
                k: WeeklyAgent._truncate_snapshot(v, max_items)
                for k, v in obj.items()
            }

        if isinstance(obj, list):
            truncated = obj[:max_items]
            note = (
                [{"_truncated": True, "original_count": len(obj)}]
                if len(obj) > max_items
                else []
            )
            return [
                WeeklyAgent._truncate_snapshot(v, max_items)
                for v in truncated
            ] + note

        return obj

    @staticmethod
    def _serialize_snapshot(snapshot: dict) -> str:

        bounded = WeeklyAgent._truncate_snapshot(snapshot)

        # Compact separators rather than indent=2: pretty-printing roughly
        # doubles the character count and the model gains nothing from it.
        text = json.dumps(bounded, separators=(",", ":"), default=str)

        return _clip(text, MAX_SNAPSHOT_CHARS, "Search Console snapshot")

    @staticmethod
    def _serialize_website(website: list[dict]) -> str:

        if not website:
            return (
                "No website page content was available. "
                "Base the analysis on Search Console data and explicitly "
                "mention the missing website/sitemap data when relevant."
            )

        bounded = website[:MAX_PAGES]

        # Keep only the fields the framework actually reasons over, and clip
        # each one. Full page records carry long heading lists that dominate
        # the prompt without changing any finding.
        compact = []

        for page in bounded:
            record = {
                "url": str(page.get("url") or "")[:MAX_FIELD_CHARS],
                "title": str(page.get("title") or "")[:MAX_FIELD_CHARS],
                "meta": str(page.get("meta_description") or "")[:MAX_FIELD_CHARS],
                "h1": [str(h)[:120] for h in (page.get("h1") or [])[:3]],
                "h2": [str(h)[:120] for h in (page.get("h2") or [])[:5]],
            }

            # Canonical only matters when it disagrees with the page url.
            canonical = str(page.get("canonical") or "")
            if canonical and canonical != record["url"]:
                record["canonical"] = canonical[:MAX_FIELD_CHARS]

            compact.append({k: v for k, v in record.items() if v})

        text = json.dumps(compact, separators=(",", ":"), default=str)

        if len(website) > MAX_PAGES:
            logger.warning(
                "Scraped %d pages, capped at %d for the prompt",
                len(website),
                MAX_PAGES,
            )
            text += (
                f"\n... ({len(website) - MAX_PAGES} more pages omitted; "
                "sample is GSC-prioritized)"
            )

        return _clip(text, MAX_PAGES * MAX_FIELD_CHARS * 3, "website pages")

    # =================================================================
    # PROMPT
    # =================================================================

    def _build_analysis_prompt(
        self,
        snapshot: dict,
        website: list[dict],
        site_url: str,
        website_number_of_pages: str,
        website_type: str,
        user_goal: str,
    ) -> str:

        # ---------------------------------------------------------
        # Website size
        # ---------------------------------------------------------

        size_context = {
            "1-10": (
                "a micro website (1-10 pages) - "
                "focus on maximizing value from limited content"
            ),
            "11-30": (
                "a small website (11-30 pages) - "
                "focus on foundational SEO and content expansion"
            ),
            "31-100": (
                "a medium-sized website (31-100 pages) - "
                "focus on content optimization and technical SEO"
            ),
            "101-300": (
                "a large website (101-300 pages) - "
                "focus on scalable SEO improvements"
            ),
            "301+": (
                "an enterprise website (301+ pages) - "
                "focus on scalable architecture and enterprise SEO"
            ),
        }.get(
            website_number_of_pages,
            f"a website with approximately {website_number_of_pages} pages",
        )

        # ---------------------------------------------------------
        # Goal
        # ---------------------------------------------------------

        goal_focus = {
            "increase organic traffic": (
                "driving more organic search traffic through "
                "keyword optimization and content strategy"
            ),
            "increase conversions/sales": (
                "improving conversions and sales through "
                "better search intent targeting and landing pages"
            ),
            "generate leads": (
                "generating qualified leads through targeted "
                "content and conversion optimization"
            ),
            "improve local visibility": (
                "improving local search visibility and local SEO"
            ),
            "build topical/brand authority": (
                "building topical authority, trust, and brand recognition"
            ),
        }.get(
            user_goal.lower(),
            user_goal,
        )

        # ---------------------------------------------------------
        # Website type
        # ---------------------------------------------------------

        type_considerations = {
            "ecommerce": (
                "Focus on product pages, category pages, "
                "product schema, internal linking, and conversions."
            ),
            "service-based": (
                "Focus on service pages, local SEO where relevant, "
                "trust signals, and lead generation."
            ),
            "content/publisher": (
                "Focus on content quality, topical authority, "
                "internal linking, authorship, and freshness."
            ),
            "saas": (
                "Focus on feature pages, comparison content, "
                "technical documentation, and signup/trial conversion."
            ),
            "other": (
                "Analyze the site's structure and adapt recommendations "
                "to the actual business."
            ),
        }.get(
            website_type.lower(),
            "",
        )

        # ---------------------------------------------------------
        # Bounded data sections
        # ---------------------------------------------------------

        snapshot_section = self._serialize_snapshot(snapshot)
        website_section = self._serialize_website(website)

        # ---------------------------------------------------------
        # System/skill instructions
        # ---------------------------------------------------------

        historical_instructions = """
## Historical Context

You have access to a historical SEO reports tool.

Use it when historical context would improve the current analysis.

The tool returns previous report summaries for this exact website.
It does NOT return complete previous reports.

Use historical summaries to:
- identify improvements or regressions
- determine whether previous issues persist
- identify recurring problems
- recognize meaningful trends
- avoid recommending an issue that appears resolved
- compare the current SEO state with previous analyses

Do not request historical reports unnecessarily.
Do not assume historical data exists.
Do not invent historical trends.

When historical reports are available, use them as supporting context,
but current Search Console and website evidence has priority.
"""

        summary_instructions = """
## Historical Summary

As part of your JSON output (see Output Format below), produce a concise
historical summary for storage alongside the full report.

The summary must describe:
- the current overall SEO state
- major positive or negative changes
- the most important issues
- important opportunities
- issues that appear persistent or resolved
- relevant metrics when available

The summary must be factual and based only on the available evidence.

Do not include generic SEO advice.
Do not invent trends.
Keep the summary concise because it will be provided to future analyses.
"""

        output_instructions = """
## Output Format

Return ONLY a single valid JSON object. No markdown code fences, no
preamble, no text before or after the JSON.

The JSON object must have exactly these two keys:

{
  "report": "<the complete SEO analysis in GitHub-flavoured Markdown, following the formatting and stage rules defined in the SEO skill>",
  "summary": "<a concise factual historical summary, significantly shorter than the report, suitable for storing in the database and using as context in future SEO analyses>"
}

Both values must be strings. Properly escape newlines, quotes, and any
other characters so the result is valid, parseable JSON. Do not wrap the
JSON in code fences.
"""

        return f"""
{self.skills_content}

You are analyzing {size_context}.

Website:
{site_url}

Website Type:
{website_type}

Primary Goal:
{goal_focus}

Website-specific considerations:
{type_considerations}

{historical_instructions}

{summary_instructions}

## Current Search Console Data

{snapshot_section}

## Current Website Content

{website_section}

## Analysis Instructions

Follow the staged SEO framework in the skill above.

This is a bounded analysis run. Do not attempt to analyze all nine stages
unless the skill explicitly permits those stages for this website size.

Use the historical reports tool when appropriate.

Compare the current state against historical summaries when useful.

Prioritize current evidence over historical assumptions.

Every recommendation must be grounded in actual Search Console or website
evidence.

Do not fabricate metrics, rankings, traffic changes, technical findings,
or historical trends.

{output_instructions}
"""

    # =================================================================
    # EXTRACT REPORT + SUMMARY
    # =================================================================

    @staticmethod
    def _extract_report_and_summary(
        response_content: str,
    ) -> tuple[str, str]:
        """
        Parse the LLM's structured JSON response into (report, summary).

        Falls back to treating the entire response as the report (with an
        empty summary) if JSON parsing fails, and logs loudly so a
        malformed run is visible in logs instead of silently dropping the
        historical summary.
        """

        text = response_content.strip()

        # Defensive: strip accidental code fences even though the prompt
        # explicitly asks the model not to use them.
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[len("json"):].strip()

        try:
            data = json.loads(text)

            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected a JSON object, got {type(data).__name__}"
                )

            report = str(data.get("report", "")).strip()
            summary = str(data.get("summary", "")).strip()

            if not report:
                raise ValueError("Parsed JSON had an empty 'report' field.")

            return report, summary

        except (json.JSONDecodeError, ValueError) as exc:

            logger.error(
                "Failed to parse structured LLM output as JSON (%s). "
                "Falling back to raw response as report with no summary. "
                "This run will NOT have a stored historical summary.",
                exc,
            )

            logger.error(
                "Raw response preview: %r",
                text[:1000],
            )

            return text, ""

    # =================================================================
    # MAIN RUN
    # =================================================================

    async def run(
        self,
        user_id: str,
        site_url: str,
        website_number_of_pages: str,
        website_type: str,
        user_goal: str,
    ):

        started_total = time.perf_counter()

        logger.info("#" * 100)
        logger.info("WEEKLY ANALYSIS STARTED")
        logger.info(
            "user_id=%s site_url=%s",
            user_id,
            site_url,
        )
        logger.info("#" * 100)

        try:

            # =====================================================
            # 1. USER CREDENTIALS
            # =====================================================

            yield "Getting Google credentials..."

            context = await self.user_tool(
                user_id=user_id,
            )

            # =====================================================
            # 2. SEARCH CONSOLE
            # =====================================================

            yield "Fetching Search Console..."

            start_date = (
                date.today() - timedelta(days=30)
            ).isoformat()

            end_date = date.today().isoformat()

            snapshot = await collect_search_console_data(
                access_token=context["access_token"],
                site_url=site_url,
                start_date=start_date,
                end_date=end_date,
            )

            logger.info(
                "Search Console data collected successfully"
            )

            # =====================================================
            # 3. SITEMAP
            # =====================================================

            sitemap = self._resolve_sitemap_url(
                snapshot,
                site_url,
            )

            logger.info(
                "Resolved sitemap=%r",
                sitemap,
            )

            # =====================================================
            # 4. WEBSITE SCRAPING
            # =====================================================

            yield "Scraping website..."

            website = await self._scrape_pages(
                sitemap
            )

            # =====================================================
            # 5. BUILD PROMPT
            # =====================================================

            prompt = self._build_analysis_prompt(
                snapshot=snapshot,
                website=website,
                site_url=site_url,
                website_number_of_pages=website_number_of_pages,
                website_type=website_type,
                user_goal=user_goal,
            )

            logger.info(
                "Analysis prompt built. Length=%d characters",
                len(prompt),
            )

            # =====================================================
            # 6. AGENT
            # =====================================================

            yield "Analyzing current and historical SEO data..."

            prompt = _enforce_prompt_budget(prompt)

            estimated_tokens = int(len(prompt) / CHARS_PER_TOKEN)

            logger.info(
                "Prompt %d/%d chars (~%d tokens) + %d output + %d safety "
                "= ~%d of %d TPM",
                len(prompt),
                MAX_PROMPT_CHARS,
                estimated_tokens,
                MAX_OUTPUT_TOKENS,
                SAFETY_TOKENS,
                estimated_tokens + MAX_OUTPUT_TOKENS + SAFETY_TOKENS,
                TPM_LIMIT,
            )

            agent = Agent(
                model=self.model,
                tools=(
                    [self.historical_reports_tool]
                    if ENABLE_HISTORICAL_TOOL
                    else []
                ),
                # Strands' default handler prints every reasoning token to
                # stdout, which floods backend.log with the model's private
                # chain of thought. The result is read from invoke_async.
                callback_handler=None,
            )

            response = await agent.invoke_async(
                prompt
            )

            response_content = (
                str(response)
                if str(response)
                else ""
            )

            if not response_content:

                raise RuntimeError(
                    "SEO agent returned an empty response."
                )

            logger.info(
                "LLM response received. Length=%d",
                len(response_content),
            )

            # =====================================================
            # 7. SPLIT REPORT + SUMMARY
            # =====================================================

            report, summary = self._extract_report_and_summary(
                response_content
            )

            logger.info(
                "Report length=%d summary length=%d",
                len(report),
                len(summary),
            )

            # =====================================================
            # 8. SAVE REPORT
            # =====================================================

            yield report

            if not summary:

                logger.warning(
                    "No historical summary generated; "
                    "report will not contain a stored summary."
                )

            else:

                logger.info(
                    "Saving SEO report and historical summary"
                )

                saved_report = (
                    await self.seo_reports_service.create_report(
                        user_id=user_id,
                        site_url=site_url,
                        report=report,
                        summary=summary,
                    )
                )

                logger.info(
                    "SEO report saved successfully. report_id=%s",
                    saved_report.id,
                )

            # =====================================================
            # 9. COMPLETE
            # =====================================================

            total_elapsed = (
                time.perf_counter()
                - started_total
            )

            logger.info("#" * 100)
            logger.info(
                "WEEKLY ANALYSIS COMPLETED"
            )
            logger.info(
                "user_id=%s",
                user_id,
            )
            logger.info(
                "site_url=%s",
                site_url,
            )
            logger.info(
                "total_duration=%.2fs",
                total_elapsed,
            )
            logger.info("#" * 100)

            yield STATUS_COMPLETED

        except Exception:

            total_elapsed = (
                time.perf_counter()
                - started_total
            )

            logger.exception(
                "WEEKLY ANALYSIS FAILED"
            )

            logger.error(
                "user_id=%s",
                user_id,
            )

            logger.error(
                "site_url=%s",
                site_url,
            )

            logger.error(
                "total_duration=%.2fs",
                total_elapsed,
            )

            yield (
                "Analysis could not be completed. "
                "Please try again, and reconnect Google if the problem "
                "continues."
            )

            # Distinct from STATUS_COMPLETED so callers can reliably tell
            # a failed run apart from a successful one instead of both
            # paths ending on the same "Completed." sentinel.
            yield STATUS_FAILED