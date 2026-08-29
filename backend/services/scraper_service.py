import logging

import httpx
from bs4 import BeautifulSoup
import lxml.etree as etree


logger = logging.getLogger(__name__)


class ScraperService:

    async def scrape_from_sitemap(
        self,
        sitemap_url: str,
    ) -> list[dict]:

        logger.info("=" * 80)
        logger.info("SCRAPER STARTED")
        logger.info("Sitemap URL: %s", sitemap_url)
        logger.info("=" * 80)

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
        ) as client:

            # =====================================================
            # 1. FETCH SITEMAP
            # =====================================================

            logger.info(
                "Fetching sitemap: %s",
                sitemap_url,
            )

            sitemap_response = await client.get(
                sitemap_url,
            )

            logger.info(
                "Sitemap response status=%s url=%s",
                sitemap_response.status_code,
                sitemap_response.url,
            )

            logger.info(
                "Sitemap response size=%d bytes",
                len(sitemap_response.content),
            )

            sitemap_response.raise_for_status()

            # =====================================================
            # 2. PARSE SITEMAP
            # =====================================================

            logger.info(
                "Parsing sitemap XML"
            )

            root = etree.fromstring(
                sitemap_response.content,
            )

            urls = root.xpath(
                "//*[local-name()='loc']/text()"
            )

            logger.info(
                "Sitemap contains %d URLs",
                len(urls),
            )

            # Log every discovered URL
            for index, url in enumerate(urls):

                logger.info(
                    "SITEMAP URL #%d: %s",
                    index + 1,
                    url,
                )

            # =====================================================
            # 3. SCRAPE PAGES
            # =====================================================

            pages = []

            for index, url in enumerate(urls):

                logger.info("")
                logger.info(
                    "-" * 80,
                )

                logger.info(
                    "SCRAPING PAGE #%d/%d",
                    index + 1,
                    len(urls),
                )

                logger.info(
                    "Original URL: %s",
                    url,
                )

                try:

                    response = await client.get(
                        url,
                    )

                    # -------------------------------------------------
                    # Response information
                    # -------------------------------------------------

                    logger.info(
                        "Response status=%s",
                        response.status_code,
                    )

                    logger.info(
                        "Final URL=%s",
                        response.url,
                    )

                    logger.info(
                        "Response size=%d bytes",
                        len(response.content),
                    )

                    # -------------------------------------------------
                    # Redirect history
                    # -------------------------------------------------

                    if response.history:

                        logger.info(
                            "Redirect chain detected"
                        )

                        for redirect_index, redirect in enumerate(
                            response.history
                        ):

                            logger.info(
                                "Redirect #%d: %s -> %s",
                                redirect_index + 1,
                                redirect.status_code,
                                redirect.headers.get(
                                    "location"
                                ),
                            )

                    else:

                        logger.info(
                            "No redirects"
                        )

                    # -------------------------------------------------
                    # Validate response
                    # -------------------------------------------------

                    response.raise_for_status()

                    # =================================================
                    # 4. PARSE HTML
                    # =================================================

                    logger.info(
                        "Parsing HTML for URL=%s",
                        response.url,
                    )

                    soup = BeautifulSoup(
                        response.text,
                        "html.parser",
                    )

                    # =================================================
                    # 5. TITLE
                    # =================================================

                    title = (
                        soup.title.get_text(strip=True)
                        if soup.title
                        else None
                    )

                    logger.info(
                        "Title=%r",
                        title,
                    )

                    # =================================================
                    # 6. META DESCRIPTION
                    # =================================================

                    meta_tag = soup.find(
                        "meta",
                        attrs={
                            "name": "description",
                        },
                    )

                    meta_description = (
                        meta_tag.get("content")
                        if meta_tag
                        else None
                    )

                    logger.info(
                        "Meta description=%r",
                        meta_description,
                    )

                    # =================================================
                    # 7. CANONICAL
                    # =================================================

                    canonical_tag = soup.find(
                        "link",
                        rel="canonical",
                    )

                    canonical = (
                        canonical_tag.get("href")
                        if canonical_tag
                        else None
                    )

                    logger.info(
                        "Canonical=%r",
                        canonical,
                    )

                    # =================================================
                    # 8. HEADINGS
                    # =================================================

                    h1 = [
                        h.get_text(strip=True)
                        for h in soup.find_all("h1")
                    ]

                    h2 = [
                        h.get_text(strip=True)
                        for h in soup.find_all("h2")
                    ]

                    logger.info(
                        "H1 count=%d values=%r",
                        len(h1),
                        h1,
                    )

                    logger.info(
                        "H2 count=%d values=%r",
                        len(h2),
                        h2,
                    )

                    # =================================================
                    # 9. STORE PAGE
                    # =================================================

                    page = {
                        "url": url,
                        "title": title,
                        "meta_description": meta_description,
                        "canonical": canonical,
                        "h1": h1,
                        "h2": h2,
                    }

                    pages.append(page)

                    logger.info(
                        "PAGE SUCCESSFULLY SCRAPED"
                    )

                    logger.info(
                        "Page data=%r",
                        page,
                    )

                except httpx.HTTPStatusError as exc:

                    logger.error(
                        "HTTP STATUS ERROR"
                    )

                    logger.error(
                        "Original URL=%s",
                        url,
                    )

                    logger.error(
                        "Status code=%s",
                        exc.response.status_code,
                    )

                    logger.error(
                        "Final URL=%s",
                        exc.response.url,
                    )

                    logger.error(
                        "Response headers=%r",
                        dict(exc.response.headers),
                    )

                    logger.error(
                        "Response body preview=%r",
                        exc.response.text[:500],
                    )

                    continue

                except httpx.RequestError as exc:

                    logger.error(
                        "HTTP REQUEST ERROR"
                    )

                    logger.error(
                        "URL=%s",
                        url,
                    )

                    logger.error(
                        "Error type=%s",
                        type(exc).__name__,
                    )

                    logger.error(
                        "Error=%s",
                        exc,
                    )

                    continue

                except Exception:

                    logger.exception(
                        "UNEXPECTED SCRAPER ERROR"
                    )

                    logger.error(
                        "URL=%s",
                        url,
                    )

                    continue

            # =====================================================
            # 10. FINAL RESULT
            # =====================================================

            # logger.info("")
            # logger.info("=" * 80)
            # logger.info("SCRAPER COMPLETED")
            # logger.info("=" * 80)

            # logger.info(
            #     "URLs discovered=%d",
            #     len(urls),
            # )

            # logger.info(
            #     "Pages successfully scraped=%d",
            #     len(pages),
            # )

            # logger.info(
            #     "Pages failed=%d",
            #     len(urls) - len(pages),
            # )

            # logger.info(
            #     "Final pages=%r",
            #     pages,
            # )

            # logger.info("=" * 80)

        return pages