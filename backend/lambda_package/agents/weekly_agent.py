import logging

from datetime import date, timedelta
from urllib.parse import urljoin

from langchain_mistralai import ChatMistralAI

from core.config import settings

from tools.search_console_tool import (
    collect_search_console_data,
)
from tools.user_context_tool import (
    create_user_context_tool,
)
from tools.website_tool import (
    scrape_website,
)


logger = logging.getLogger(__name__)


class WeeklyAgent:

    def __init__(self, db):

        self.user_tool = create_user_context_tool(db)

        self.llm = ChatMistralAI(
    model_name="mistral-large-latest",
    api_key=settings.MISTRAL_API_KEY,
    temperature=0,
)

    @staticmethod
    def _resolve_sitemap_url(
        snapshot: dict,
        site_url: str,
    ) -> str | None:
        """
        Pick a sitemap URL to scrape, or None when the site has none.

        Search Console answers the sitemaps endpoint with an empty object when
        the owner has never submitted a sitemap, so neither the "sitemap" key
        nor any entry is guaranteed to exist.
        """

        entries = (
            snapshot.get("sitemaps")
            or {}
        ).get("sitemap") or []

        for entry in entries:

            path = entry.get("path")

            if path:
                return path

        # Nothing submitted. A conventional /sitemap.xml is worth one attempt,
        # but only for URL-prefix properties; domain properties are addressed
        # as "sc-domain:example.com" and cannot be joined into a URL.
        if site_url.startswith(("http://", "https://")):
            return urljoin(site_url, "/sitemap.xml")

        return None

    async def _scrape_pages(
        self,
        sitemap_url: str | None,
    ) -> list[dict]:
        """
        Scrape sitemap pages, degrading to an empty list on failure.

        Page content enriches the recommendation but is not required for it, so
        an unreachable or non-XML sitemap must not end the analysis.
        """

        if sitemap_url is None:
            return []

        try:

            return await scrape_website.ainvoke(
                {
                    "sitemap_url": sitemap_url,
                }
            )

        except Exception:

            logger.warning(
                "Sitemap scrape failed for %s; "
                "continuing with Search Console data only.",
                sitemap_url,
                exc_info=True,
            )

            return []

    async def run(
        self,
        user_id: str,
        site_url: str,
    ):

        try:

            yield "Getting Google credentials..."

            context = await self.user_tool.ainvoke(
                {
                    "user_id": user_id,
                }
            )

            yield "Fetching Search Console..."

            snapshot = await collect_search_console_data.ainvoke(
                {
                    "access_token": context["access_token"],
                    "site_url": site_url,
                    "start_date": (
                        date.today() - timedelta(days=30)
                    ).isoformat(),
                    "end_date": date.today().isoformat(),
                }
            )

            sitemap = self._resolve_sitemap_url(
                snapshot,
                site_url,
            )

            yield "Scraping website..."

            website = await self._scrape_pages(sitemap)

            yield "Thinking..."

            website_section = (
                website
                if website
                else (
                    "No page content available. No sitemap is submitted in "
                    "Search Console and none could be read from the site, so "
                    "base your answer on the Search Console data alone and "
                    "mention the missing sitemap."
                )
            )

            prompt = f"""
Search Console:

{snapshot}

Website:

{website_section}

Give me the five highest-impact SEO improvements.

Format the answer as GitHub-flavoured Markdown, because the dashboard renders
it as Markdown rather than plain text:

- Open with one `##` sentence summarising the account's current state.
- Give each improvement its own `###` heading, numbered 1 to 5, ordered by
  impact. Put the plain title in the heading with no bold markers around it.
- Under each heading use `**Issue**`, `**Fix**`, and `**Why it matters**` as
  bold inline labels, followed by short bullet lists.
- Quote every query, URL, and metric from the data above so each claim is
  traceable. Use backticks for queries, URLs, and tag names.
- Use a Markdown table when comparing more than two numbers.
- Do not use emoji, horizontal rules, or bold text inside headings.
- Do not wrap the whole response in a code fence.
"""

            response = await self.llm.ainvoke(prompt)

            yield response.content

            yield "Completed."

        except Exception:

            # Without this the generator raises mid-response, the chunked body
            # is cut off, and the browser reports ERR_INCOMPLETE_CHUNKED_ENCODING
            # with no explanation. Full detail stays in the server log.
            logger.exception(
                "Weekly analysis failed for user=%s site=%s",
                user_id,
                site_url,
            )

            yield (
                "Analysis could not be completed. "
                "Please try again, and reconnect Google if the problem "
                "continues."
            )

            yield "Completed."