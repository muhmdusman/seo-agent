import httpx

from bs4 import BeautifulSoup
import lxml.etree as etree


class ScraperService:

    async def scrape_from_sitemap(
        self,
        sitemap_url: str,
    ) -> list[dict]:

        async with httpx.AsyncClient(timeout=30) as client:

            sitemap_response = await client.get(
                sitemap_url,
            )

            sitemap_response.raise_for_status()

            root = etree.fromstring(
                sitemap_response.content,
            )

            urls = root.xpath(
                "//*[local-name()='loc']/text()"
            )

            pages = []

            for url in urls:

                try:

                    response = await client.get(url)

                    response.raise_for_status()

                    soup = BeautifulSoup(
                        response.text,
                        "html.parser",
                    )

                    title = (
                        soup.title.get_text(strip=True)
                        if soup.title
                        else None
                    )

                    meta_tag = soup.find(
                        "meta",
                        attrs={
                            "name": "description",
                        },
                    )

                    canonical_tag = soup.find(
                        "link",
                        rel="canonical",
                    )

                    pages.append(
                        {
                            "url": url,
                            "title": title,
                            "meta_description": (
                                meta_tag.get("content")
                                if meta_tag
                                else None
                            ),
                            "canonical": (
                                canonical_tag.get("href")
                                if canonical_tag
                                else None
                            ),
                            "h1": [
                                h.get_text(strip=True)
                                for h in soup.find_all("h1")
                            ],
                            "h2": [
                                h.get_text(strip=True)
                                for h in soup.find_all("h2")
                            ],
                        }
                    )

                except httpx.HTTPError:
                    continue

        return pages