from langchain.tools import tool

from services.scraper_service import ScraperService


scraper_service = ScraperService()


@tool
async def scrape_website(
    sitemap_url: str,
):
    """
    Scrape every page contained in a sitemap.
    """

    return await scraper_service.scrape_from_sitemap(
        sitemap_url=sitemap_url,
    )