import asyncio
import logging

from services.scraper_service import ScraperService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main():

    scraper = ScraperService()

    pages = await scraper.scrape_from_sitemap(
        "https://www.bitoreal.pk/sitemap.xml"
    )

    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    print(f"Pages scraped: {len(pages)}")

    for page in pages:
        print("\n", page)


if __name__ == "__main__":
    asyncio.run(main())