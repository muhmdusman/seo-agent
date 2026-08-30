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


# Adjust this path if your skills.md lives somewhere else.
SKILLS_PATH = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "staged-seo-growth-agent"
    / "SKILL.md"
)


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

        self.skills_content = self._load_skills()

        # ---------------------------------------------------------
        # LLM
        # ---------------------------------------------------------

        logger.info("Initializing Mistral LLM")

        self.model = LiteLLMModel(
            model_id="mistral/mistral-small-latest",
            client_args={
                "api_key": settings.MISTRAL_API_KEY,
            },
            params={
                "temperature": 0,
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
        # Website data
        # ---------------------------------------------------------

        if website:

            website_section = website

        else:

            website_section = (
                "No website page content was available. "
                "Base the analysis on Search Console data and explicitly "
                "mention the missing website/sitemap data when relevant."
            )

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

After producing the current SEO analysis, produce a concise historical
summary for storage.

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

{snapshot}

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

## Output Format

Return exactly two sections:

## SEO Report

Write the complete SEO analysis in GitHub-flavoured Markdown.

Follow the formatting and stage rules defined in the SEO skill.

## Historical Summary

Write a concise factual summary suitable for storing in the database
and using as context in future SEO analyses.

The summary should be significantly shorter than the full report.
"""

    # =================================================================
    # EXTRACT REPORT + SUMMARY
    # =================================================================

    @staticmethod
    def _extract_report_and_summary(
        response_content: str,
    ) -> tuple[str, str]:

        marker = "## Historical Summary"

        if marker not in response_content:

            logger.warning(
                "Historical Summary section was not found in LLM response."
            )

            return (
                response_content.strip(),
                "",
            )

        report, summary = response_content.split(
            marker,
            1,
        )

        # Remove our report heading if present.
        report = report.strip()

        if report.startswith("## SEO Report"):
            report = report[len("## SEO Report"):].strip()

        summary = summary.strip()

        return report, summary

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

            agent = Agent(
                model=self.model,
                tools=[
                    self.historical_reports_tool,
                ],
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

            yield "Completed."

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

            yield "Completed."