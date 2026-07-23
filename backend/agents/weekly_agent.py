from datetime import date, timedelta
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


class WeeklyAgent:

    def __init__(self, db):

        self.user_tool = create_user_context_tool(db)

        self.llm = ChatMistralAI(
    model_name="mistral-large-latest",
    api_key=settings.MISTRAL_API_KEY,
    temperature=0,
)
    async def run(
        self,
        user_id: str,
        site_url: str,
    ):

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

        sitemap = snapshot["sitemaps"]["sitemap"][0]["path"]

        yield "Scraping website..."

        website = await scrape_website.ainvoke(
            {
                "sitemap_url": sitemap,
            }
        )

        yield "Thinking..."

        prompt = f"""
Search Console:

{snapshot}

Website:

{website}

Give me the five highest-impact SEO improvements.
"""

        response = await self.llm.ainvoke(prompt)

        yield response.content

        yield "Completed."