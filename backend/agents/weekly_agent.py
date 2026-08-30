import logging
import time
from datetime import date, timedelta
from urllib.parse import urljoin

from strands import Agent
from strands.models.litellm import LiteLLMModel

from core.config import settings
from tools.search_console_tool import collect_search_console_data
from tools.user_context_tool import create_user_context_tool
from tools.website_tool import scrape_website


logger = logging.getLogger(__name__)


class WeeklyAgent:
    """
    Weekly SEO analysis agent.

    This version contains extensive logging so every major checkpoint
    can be inspected during sitemap debugging.
    """

    def __init__(self, db):

        logger.info("=" * 100)
        logger.info("INITIALIZING WEEKLY AGENT")
        logger.info("=" * 100)

        logger.debug(
            "Database object type=%s",
            type(db).__name__,
        )

        # ---------------------------------------------------------
        # User context tool
        # ---------------------------------------------------------

        logger.info(
            "Creating user context tool"
        )

        self.user_tool = create_user_context_tool(db)

        logger.info(
            "User context tool created type=%s",
            type(self.user_tool).__name__,
        )

        # ---------------------------------------------------------
        # LLM
        # ---------------------------------------------------------

        logger.info(
            "Initializing Mistral LLM"
        )

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
            "Mistral LLM initialized model=%s timeout=%s "
            "max_retries=%s temperature=%s",
            "mistral/mistral-small-latest",
            120,
            3,
            0,
        )

        logger.info("=" * 100)
        logger.info("WEEKLY AGENT INITIALIZED")
        logger.info("=" * 100)

    # =================================================================
    # SITEMAP RESOLUTION
    # =================================================================

    @staticmethod
    def _resolve_sitemap_url(
        snapshot: dict,
        site_url: str,
    ) -> str | None:

        logger.info("")
        logger.info("=" * 100)
        logger.info("CHECKPOINT: SITEMAP RESOLUTION START")
        logger.info("=" * 100)

        logger.info(
            "Site URL received=%r",
            site_url,
        )

        logger.info(
            "Snapshot type=%s",
            type(snapshot).__name__,
        )

        # ---------------------------------------------------------
        # Validate snapshot
        # ---------------------------------------------------------

        if not isinstance(snapshot, dict):

            logger.error(
                "SITEMAP RESOLUTION ERROR: snapshot is not a dict"
            )

            logger.error(
                "Snapshot value=%r",
                snapshot,
            )

            return None

        # ---------------------------------------------------------
        # Snapshot keys
        # ---------------------------------------------------------

        logger.info(
            "Snapshot top-level keys=%s",
            list(snapshot.keys()),
        )

        # ---------------------------------------------------------
        # FULL SNAPSHOT
        # ---------------------------------------------------------

        logger.info(
            "FULL SEARCH CONSOLE SNAPSHOT:"
        )

        logger.info(
            "%r",
            snapshot,
        )

        # ---------------------------------------------------------
        # Check whether sitemaps exists
        # ---------------------------------------------------------

        if "sitemaps" not in snapshot:

            logger.error(
                "!!! SITEMAPS KEY DOES NOT EXIST IN SNAPSHOT !!!"
            )

            logger.error(
                "Available keys=%s",
                list(snapshot.keys()),
            )

            logger.warning(
                "This means the sitemap information never reached "
                "WeeklyAgent from collect_search_console_data."
            )

        else:

            logger.info(
                "SITEMAPS KEY EXISTS IN SNAPSHOT"
            )

        # ---------------------------------------------------------
        # Get sitemap data
        # ---------------------------------------------------------

        sitemaps_data = snapshot.get("sitemaps")

        logger.info(
            "snapshot.get('sitemaps') type=%s",
            type(sitemaps_data).__name__,
        )

        logger.info(
            "snapshot.get('sitemaps') value=%r",
            sitemaps_data,
        )

        # ---------------------------------------------------------
        # Handle dictionary structure
        # ---------------------------------------------------------

        if isinstance(sitemaps_data, dict):

            logger.info(
                "Sitemaps is a dictionary"
            )

            logger.info(
                "Sitemaps dictionary keys=%s",
                list(sitemaps_data.keys()),
            )

            sitemap_entries = sitemaps_data.get("sitemap")

            logger.info(
                "sitemaps_data.get('sitemap') type=%s",
                type(sitemap_entries).__name__,
            )

            logger.info(
                "sitemaps_data.get('sitemap') value=%r",
                sitemap_entries,
            )

        # ---------------------------------------------------------
        # Handle list structure
        # ---------------------------------------------------------

        elif isinstance(sitemaps_data, list):

            logger.info(
                "Sitemaps is already a list"
            )

            sitemap_entries = sitemaps_data

        # ---------------------------------------------------------
        # Missing / unexpected
        # ---------------------------------------------------------

        else:

            logger.warning(
                "Sitemap data is missing or has unexpected type"
            )

            logger.warning(
                "Unexpected sitemap data type=%s",
                type(sitemaps_data).__name__,
            )

            sitemap_entries = []

        # ---------------------------------------------------------
        # Normalize
        # ---------------------------------------------------------

        if sitemap_entries is None:

            logger.warning(
                "Sitemap entries are None; converting to empty list"
            )

            sitemap_entries = []

        if not isinstance(sitemap_entries, list):

            logger.error(
                "Sitemap entries are NOT a list"
            )

            logger.error(
                "Entries type=%s value=%r",
                type(sitemap_entries).__name__,
                sitemap_entries,
            )

            sitemap_entries = []

        # ---------------------------------------------------------
        # Number of sitemap entries
        # ---------------------------------------------------------

        logger.info(
            "TOTAL SITEMAP ENTRIES=%d",
            len(sitemap_entries),
        )

        # ---------------------------------------------------------
        # Inspect every sitemap
        # ---------------------------------------------------------

        for index, entry in enumerate(sitemap_entries):

            logger.info("")
            logger.info(
                "--- SITEMAP ENTRY #%d ---",
                index,
            )

            logger.info(
                "Entry type=%s",
                type(entry).__name__,
            )

            logger.info(
                "Entry value=%r",
                entry,
            )

            if not isinstance(entry, dict):

                logger.warning(
                    "Sitemap entry #%d is not a dictionary",
                    index,
                )

                continue

            logger.info(
                "Entry keys=%s",
                list(entry.keys()),
            )

            for key, value in entry.items():

                logger.info(
                    "Entry[%r] type=%s value=%r",
                    key,
                    type(value).__name__,
                    value,
                )

            path = entry.get("path")

            logger.info(
                "Extracted sitemap path=%r",
                path,
            )

            if path:

                logger.info("")
                logger.info(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                )
                logger.info(
                    "SEARCH CONSOLE SITEMAP FOUND"
                )
                logger.info(
                    "SITEMAP URL=%s",
                    path,
                )
                logger.info(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                )
                logger.info("")

                return path

        # ---------------------------------------------------------
        # No submitted sitemap
        # ---------------------------------------------------------

        logger.warning("")
        logger.warning(
            "NO SEARCH CONSOLE SITEMAP FOUND"
        )
        logger.warning(
            "Number of sitemap entries=%d",
            len(sitemap_entries),
        )

        # ---------------------------------------------------------
        # Fallback
        # ---------------------------------------------------------

        logger.info(
            "Checking whether fallback sitemap can be constructed"
        )

        logger.info(
            "site_url=%r",
            site_url,
        )

        if site_url.startswith(("http://", "https://")):

            fallback = urljoin(
                site_url,
                "/sitemap.xml",
            )

            logger.warning("")
            logger.warning(
                "USING FALLBACK SITEMAP"
            )
            logger.warning(
                "Fallback sitemap URL=%s",
                fallback,
            )
            logger.warning("")

            return fallback

        logger.error(
            "Cannot construct fallback sitemap."
        )

        logger.error(
            "site_url does not start with http:// or https://"
        )

        logger.error(
            "site_url=%r",
            site_url,
        )

        return None

    # =================================================================
    # WEBSITE SCRAPER
    # =================================================================

    async def _scrape_pages(
        self,
        sitemap_url: str | None,
    ) -> list[dict]:

        logger.info("")
        logger.info("=" * 100)
        logger.info("CHECKPOINT: WEBSITE SCRAPING START")
        logger.info("=" * 100)

        logger.info(
            "Sitemap URL passed to scraper=%r",
            sitemap_url,
        )

        # ---------------------------------------------------------
        # No sitemap
        # ---------------------------------------------------------

        if sitemap_url is None:

            logger.warning(
                "No sitemap URL available."
            )

            logger.warning(
                "Website scraping will be skipped."
            )

            return []

        # ---------------------------------------------------------
        # Start timer
        # ---------------------------------------------------------

        started = time.perf_counter()

        logger.info(
            "Calling scrape_website.ainvoke()"
        )

        logger.info(
            "Tool input:"
        )

        logger.info(
            "%r",
            {
                "sitemap_url": sitemap_url,
            },
        )

        try:

            result = await scrape_website(
                sitemap_url=sitemap_url,
            )

            elapsed = time.perf_counter() - started

            # -----------------------------------------------------
            # Raw result
            # -----------------------------------------------------

            logger.info("")
            logger.info(
                "SCRAPER RAW RESPONSE RECEIVED"
            )

            logger.info(
                "Result type=%s",
                type(result).__name__,
            )

            logger.info(
                "Result value=%r",
                result,
            )

            # -----------------------------------------------------
            # Result length
            # -----------------------------------------------------

            try:

                result_length = len(result)

            except TypeError:

                result_length = None

            logger.info(
                "Result length=%s",
                result_length,
            )

            logger.info(
                "Scraper duration=%.2fs",
                elapsed,
            )

            # -----------------------------------------------------
            # Inspect pages
            # -----------------------------------------------------

            if isinstance(result, list):

                logger.info(
                    "Scraper returned LIST with %d items",
                    len(result),
                )

                for index, page in enumerate(result):

                    logger.info("")
                    logger.info(
                        "--- SCRAPED PAGE #%d ---",
                        index,
                    )

                    logger.info(
                        "Page type=%s",
                        type(page).__name__,
                    )

                    logger.info(
                        "Page value=%r",
                        page,
                    )

                    if isinstance(page, dict):

                        logger.info(
                            "Page keys=%s",
                            list(page.keys()),
                        )

                        for key, value in page.items():

                            logger.info(
                                "Page[%r] type=%s value=%r",
                                key,
                                type(value).__name__,
                                value,
                            )

            elif isinstance(result, dict):

                logger.info(
                    "Scraper returned DICT"
                )

                logger.info(
                    "Dictionary keys=%s",
                    list(result.keys()),
                )

                for key, value in result.items():

                    logger.info(
                        "Result[%r] type=%s value=%r",
                        key,
                        type(value).__name__,
                        value,
                    )

            else:

                logger.warning(
                    "Scraper returned unexpected type=%s",
                    type(result).__name__,
                )

            logger.info("=" * 100)
            logger.info("CHECKPOINT: WEBSITE SCRAPING COMPLETE")
            logger.info("=" * 100)

            return result

        except Exception:

            elapsed = time.perf_counter() - started

            logger.exception(
                "!!! WEBSITE SCRAPING FAILED !!!"
            )

            logger.error(
                "Sitemap URL=%r",
                sitemap_url,
            )

            logger.error(
                "Scraper duration=%.2fs",
                elapsed,
            )

            logger.warning(
                "Continuing with Search Console data only"
            )

            return []

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

        logger.info("")
        logger.info("#" * 100)
        logger.info(
            "WEEKLY ANALYSIS STARTED"
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
            "website_number_of_pages=%s",
            website_number_of_pages,
        )
        logger.info(
            "website_type=%s",
            website_type,
        )
        logger.info(
            "user_goal=%s",
            user_goal,
        )
        logger.info("#" * 100)

        try:

            # =====================================================
            # 1. USER CREDENTIALS
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 1: FETCHING USER CREDENTIALS")
            logger.info("=" * 100)

            yield "Getting Google credentials..."

            started = time.perf_counter()

            context = await self.user_tool(
                user_id=user_id,
            )

            elapsed = time.perf_counter() - started

            logger.info(
                "User context response received"
            )

            logger.info(
                "Context type=%s",
                type(context).__name__,
            )

            logger.info(
                "Context keys=%s",
                list(context.keys())
                if isinstance(context, dict)
                else None,
            )

            # -----------------------------------------------------
            # IMPORTANT:
            # Do NOT log the actual OAuth token.
            # -----------------------------------------------------

            if isinstance(context, dict):

                logger.info(
                    "Context full response=%r",
                    {
                        key: (
                            "<REDACTED ACCESS TOKEN>"
                            if key == "access_token"
                            else value
                        )
                        for key, value in context.items()
                    },
                )

                access_token = context.get(
                    "access_token"
                )

                logger.info(
                    "Access token exists=%s",
                    access_token is not None,
                )

                if access_token is not None:

                    logger.info(
                        "Access token type=%s",
                        type(access_token).__name__,
                    )

                    logger.info(
                        "Access token length=%d",
                        len(access_token),
                    )

            else:

                logger.error(
                    "User context response is not a dictionary"
                )

            logger.info(
                "Credential retrieval duration=%.2fs",
                elapsed,
            )

            # =====================================================
            # 2. SEARCH CONSOLE
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 2: SEARCH CONSOLE DATA")
            logger.info("=" * 100)

            logger.info(
                "Preparing Search Console request"
            )

            logger.info(
                "user_id=%s",
                user_id,
            )

            logger.info(
                "site_url=%s",
                site_url,
            )

            start_date = (
                date.today() - timedelta(days=30)
            ).isoformat()

            end_date = date.today().isoformat()

            logger.info(
                "start_date=%s",
                start_date,
            )

            logger.info(
                "end_date=%s",
                end_date,
            )

            yield "Fetching Search Console..."

            started = time.perf_counter()

            logger.info(
                "Calling collect_search_console_data.ainvoke()"
            )

            tool_input = {
                "access_token": context["access_token"],
                "site_url": site_url,
                "start_date": start_date,
                "end_date": end_date,
            }

            logger.info(
                "Search Console tool input keys=%s",
                list(tool_input.keys()),
            )

            logger.info(
                "Search Console tool site_url=%r",
                tool_input["site_url"],
            )

            logger.info(
                "Search Console tool start_date=%r",
                tool_input["start_date"],
            )

            logger.info(
                "Search Console tool end_date=%r",
                tool_input["end_date"],
            )

            snapshot = await collect_search_console_data(
                access_token=tool_input["access_token"],
                site_url=tool_input["site_url"],
                start_date=tool_input["start_date"],
                end_date=tool_input["end_date"],
            )

            elapsed = time.perf_counter() - started

            # -----------------------------------------------------
            # RAW SEARCH CONSOLE RESPONSE
            # -----------------------------------------------------

            logger.info("")
            logger.info(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )
            logger.info(
                "RAW SEARCH CONSOLE RESPONSE"
            )
            logger.info(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )

            logger.info(
                "Snapshot type=%s",
                type(snapshot).__name__,
            )

            logger.info(
                "Snapshot value=%r",
                snapshot,
            )

            logger.info(
                "Search Console duration=%.2fs",
                elapsed,
            )

            # -----------------------------------------------------
            # Snapshot inspection
            # -----------------------------------------------------

            if isinstance(snapshot, dict):

                logger.info("")
                logger.info(
                    "SEARCH CONSOLE SNAPSHOT STRUCTURE"
                )

                logger.info(
                    "Number of top-level keys=%d",
                    len(snapshot),
                )

                logger.info(
                    "Top-level keys=%s",
                    list(snapshot.keys()),
                )

                for key, value in snapshot.items():

                    logger.info("")
                    logger.info(
                        "SNAPSHOT FIELD=%r",
                        key,
                    )

                    logger.info(
                        "Field type=%s",
                        type(value).__name__,
                    )

                    logger.info(
                        "Field value=%r",
                        value,
                    )

            else:

                logger.error(
                    "Search Console returned a non-dict snapshot"
                )

            # =====================================================
            # 3. SITEMAP
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 3: RESOLVING SITEMAP")
            logger.info("=" * 100)

            sitemap = self._resolve_sitemap_url(
                snapshot,
                site_url,
            )

            logger.info("")
            logger.info(
                "FINAL RESOLVED SITEMAP"
            )

            logger.info(
                "sitemap=%r",
                sitemap,
            )

            if sitemap:

                logger.info(
                    "Sitemap URL successfully resolved"
                )

            else:

                logger.warning(
                    "Sitemap URL could NOT be resolved"
                )

            # =====================================================
            # 4. WEBSITE SCRAPING
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 4: WEBSITE SCRAPING")
            logger.info("=" * 100)

            yield "Scraping website..."

            website = await self._scrape_pages(
                sitemap
            )

            logger.info("")
            logger.info(
                "WEBSITE SCRAPING FINAL RESULT"
            )

            logger.info(
                "Website type=%s",
                type(website).__name__,
            )

            logger.info(
                "Website page count=%d",
                len(website)
                if isinstance(website, list)
                else -1,
            )

            logger.info(
                "Website full value=%r",
                website,
            )

            # =====================================================
            # 5. BUILD PROMPT
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 5: BUILDING LLM PROMPT")
            logger.info("=" * 100)

            logger.info(
                "Website number of pages=%s",
                website_number_of_pages,
            )

            logger.info(
                "Website type=%s",
                website_type,
            )

            logger.info(
                "User goal=%s",
                user_goal,
            )

            if website:

                website_section = website

                logger.info(
                    "Website content available for prompt"
                )

                logger.info(
                    "Website pages=%d",
                    len(website),
                )

            else:

                website_section = (
                    "No page content available. No sitemap is submitted in "
                    "Search Console and none could be read from the site, so "
                    "base your answer on the Search Console data alone and "
                    "mention the missing sitemap."
                )

                logger.warning(
                    "No website content available."
                )

            # Map website size to context
            size_context = {
                "1-10": "a micro website (1-10 pages) - focus on maximizing value from limited content",
                "11-30": "a small website (11-30 pages) - focus on foundational SEO and content expansion opportunities",
                "31-100": "a medium-sized website (31-100 pages) - focus on content optimization and technical SEO",
                "101-300": "a large website (101-300 pages) - focus on scaling SEO efforts and automation",
                "301+": "an enterprise website (301+ pages) - focus on enterprise-level SEO strategy and site architecture"
            }.get(website_number_of_pages, "")

            # Map user goal to specific focus
            goal_focus = {
                "increase organic traffic": "driving more organic search traffic through keyword optimization and content strategy",
                "increase conversions/sales": "improving conversion rates and sales through better user intent targeting and landing page optimization",
                "generate leads": "generating qualified leads through targeted content and conversion optimization",
                "improve local visibility": "enhancing local search presence through local SEO tactics and Google Business Profile optimization",
                "build topical/brand authority": "establishing topical authority and brand recognition through content depth and E-E-A-T signals"
            }.get(user_goal.lower(), user_goal)

            # Website type specific considerations
            type_considerations = {
                "ecommerce": "Focus on product pages, category optimization, structured data for products, and conversion funnels.",
                "service-based": "Focus on service pages, local SEO if applicable, trust signals, and lead generation.",
                "content/publisher": "Focus on content quality, topical authority, internal linking, and user engagement metrics.",
                "saas": "Focus on feature pages, comparison content, trial/signup conversion optimization, and technical documentation.",
                "other": "Analyze the site structure and provide tailored recommendations."
            }.get(website_type.lower(), "")

            prompt = f"""
You are analyzing {size_context}.

Website Type: {website_type}
Primary Goal: {goal_focus}

{type_considerations}

Search Console Data:

{snapshot}

Website Content:

{website_section}

Based on the above context, provide the five highest-impact SEO improvements specifically tailored to:
- The website's size ({website_number_of_pages} pages)
- The business type ({website_type})
- The primary goal ({user_goal})

Format the answer as GitHub-flavoured Markdown, because the dashboard renders 
it as Markdown rather than plain text:

- Open with one `##` sentence summarising the account's current state and how it relates to their goal of {user_goal}.
- Give each improvement its own `###` heading, numbered 1 to 5, ordered by 
  impact for achieving "{user_goal}". Put the plain title in the heading with no bold markers around it.
- Under each heading use `**Issue**`, `**Fix**`, and `**Why it matters**` as 
  bold inline labels, followed by short bullet lists.
- In the "Why it matters" section, explicitly connect each recommendation to the user's goal of {user_goal}.
- Quote every query, URL, and metric from the data above so each claim is 
  traceable. Use backticks for queries, URLs, and tag names.
- Use a Markdown table when comparing more than two numbers.
- Do not use emoji, horizontal rules, or bold text inside headings.
- Do not wrap the whole response in a code fence.
- Tailor recommendations to the website type ({website_type}) - for example, for ecommerce sites prioritize product page optimization, for service-based sites focus on local SEO and trust signals.
"""

            logger.info(
                "Prompt built successfully"
            )

            logger.info(
                "Prompt length=%d characters",
                len(prompt),
            )

            logger.debug(
                "FULL LLM PROMPT:\n%s",
                prompt,
            )

            # =====================================================
            # 6. LLM
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 6: CALLING MISTRAL")
            logger.info("=" * 100)

            yield "Thinking..."

            started = time.perf_counter()

            logger.info(
                "Sending prompt to Mistral"
            )

            agent = Agent(model=self.model, tools=[])
            response = await agent.invoke_async(prompt)

            elapsed = time.perf_counter() - started

            logger.info(
                "Mistral response received"
            )

            logger.info(
                "Response type=%s",
                type(response).__name__,
            )

            logger.info(
                "Response object=%r",
                response,
            )

            response_content = (
                str(response)
                if str(response)
                else ""
            )

            logger.info(
                "Response content length=%d",
                len(response_content),
            )

            logger.info(
                "FULL MISTRAL RESPONSE:"
            )

            logger.info(
                "\n%s",
                response_content,
            )

            logger.info(
                "Mistral duration=%.2fs",
                elapsed,
            )

            # =====================================================
            # 7. FINAL REPORT
            # =====================================================

            logger.info("")
            logger.info("=" * 100)
            logger.info("CHECKPOINT 7: STREAMING FINAL REPORT")
            logger.info("=" * 100)

            logger.info(
                "Final report length=%d",
                len(response_content),
            )

            yield response_content

            # =====================================================
            # 8. COMPLETE
            # =====================================================

            total_elapsed = (
                time.perf_counter()
                - started_total
            )

            logger.info("")
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
                "sitemap=%r",
                sitemap,
            )
            logger.info(
                "website_pages=%d",
                len(website),
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

            logger.exception("")
            logger.exception(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )
            logger.exception(
                "WEEKLY ANALYSIS FAILED"
            )
            logger.exception(
                "user_id=%s",
                user_id,
            )
            logger.exception(
                "site_url=%s",
                site_url,
            )
            logger.exception(
                "total_duration=%.2fs",
                total_elapsed,
            )
            logger.exception(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )

            yield (
                "Analysis could not be completed. "
                "Please try again, and reconnect Google if the problem "
                "continues."
            )

            yield "Completed."