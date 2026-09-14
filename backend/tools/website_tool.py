from strands import tool

from services.scraper_service import ScraperService


scraper_service = ScraperService()


@tool
async def scrape_website(
    sitemap_url: str,
    max_pages: int = 12,
    priority_urls: list[str] | None = None,
    site_url: str | None = None,
):
    """
    Sample a bounded set of public pages, prioritizing saved task URLs.
    """

    return await scraper_service.scrape_from_sitemap(
        sitemap_url=sitemap_url,
        max_pages=max_pages, priority_urls=priority_urls, site_url=site_url,
    )
