from datetime import date
from urllib.parse import quote
from urllib.parse import urlsplit

import asyncio
import logging

import httpx

from services.scraper_service import belongs_to_property


logger = logging.getLogger(__name__)


def verified_property_match(sites: dict, requested_site_url: str) -> str | None:
    """Return the verified Search Console property that can serve this request."""
    for site in sites.get("siteEntry", []):
        if site.get("permissionLevel") == "siteUnverifiedUser":
            continue
        owned = site.get("siteUrl", "")
        if property_covers_request(owned, requested_site_url):
            return owned
    return None


def property_covers_request(owned_site_url: str, requested_site_url: str) -> bool:
    """Check GSC property coverage across sc-domain and URL-prefix forms."""
    if owned_site_url == requested_site_url:
        return True
    if requested_site_url.startswith(("http://", "https://")):
        return belongs_to_property(requested_site_url, owned_site_url)
    if requested_site_url.startswith("sc-domain:"):
        domain = requested_site_url.removeprefix("sc-domain:").strip("/").lower()
        if owned_site_url.startswith("sc-domain:"):
            return owned_site_url.removeprefix("sc-domain:").strip("/").lower() == domain
        try:
            hostname = (urlsplit(owned_site_url).hostname or "").lower()
        except ValueError:
            return False
        return hostname == domain or hostname.endswith("." + domain)
    return False


class SearchConsoleService:

    BASE_URL = "https://searchconsole.googleapis.com/webmasters/v3"

    async def page_performance(self, access_token: str, site_url: str, page_url: str,
                               start_date: date, end_date: date):
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{self.BASE_URL}/sites/{quote(site_url, safe='')}/searchAnalytics/query",
                headers=self._headers(access_token),
                json={"startDate": start_date.isoformat(), "endDate": end_date.isoformat(),
                      "dimensions": ["date"], "type": "web", "dataState": "final", "rowLimit": 32,
                      "dimensionFilterGroups": [{"filters": [
                          {"dimension": "page", "operator": "equals", "expression": page_url},
                      ]}]},
            )
            response.raise_for_status()
            return response.json()

    def _headers(
        self,
        access_token: str,
    ):
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    async def _query(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
        dimensions: list[str],
        row_limit: int = 100,
    ):

        response = await client.post(
            (
                f"{self.BASE_URL}/sites/"
                f"{quote(site_url, safe='')}"
                "/searchAnalytics/query"
            ),
            headers=self._headers(access_token),
            json={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": dimensions,
                "rowLimit": row_limit,
            },
        )

        if response.status_code >= 400:
            logger.error(
                "Search Console API error: "
                f"status={response.status_code}, "
                f"site={site_url}, "
                f"dimensions={dimensions}, "
                f"response={response.text}"
            )

        response.raise_for_status()

        return response.json()

    async def list_sites(
        self,
        access_token: str,
    ):

        async with httpx.AsyncClient() as client:

            response = await client.get(
                f"{self.BASE_URL}/sites",
                headers=self._headers(access_token),
            )

            if response.status_code >= 400:
                logger.error(
                    "Search Console sites request failed: "
                    f"status={response.status_code}, "
                    f"response={response.text}"
                )

            response.raise_for_status()

            return response.json()

    async def get_queries(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        return await self._query(
            client,
            access_token,
            site_url,
            start_date,
            end_date,
            ["query"],
        )

    async def get_pages(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        return await self._query(
            client,
            access_token,
            site_url,
            start_date,
            end_date,
            ["page"],
        )

    async def get_devices(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        return await self._query(
            client,
            access_token,
            site_url,
            start_date,
            end_date,
            ["device"],
        )

    async def get_countries(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        return await self._query(
            client,
            access_token,
            site_url,
            start_date,
            end_date,
            ["country"],
        )

    async def get_daily_performance(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        return await self._query(
            client,
            access_token,
            site_url,
            start_date,
            end_date,
            ["date"],
        )

    async def get_sitemaps(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        site_url: str,
    ):

        response = await client.get(
            (
                f"{self.BASE_URL}/sites/"
                f"{quote(site_url, safe='')}"
                "/sitemaps"
            ),
            headers=self._headers(access_token),
        )

        if response.status_code >= 400:
            logger.error(
                "Search Console sitemap request failed: "
                f"status={response.status_code}, "
                f"site={site_url}, "
                f"response={response.text}"
            )

        response.raise_for_status()

        return response.json()

    async def collect_site_snapshot(
        self,
        access_token: str,
        site_url: str,
        start_date: date,
        end_date: date,
    ):

        async with httpx.AsyncClient() as client:

            (
                queries,
                pages,
                devices,
                countries,
                daily,
                sitemaps,
            ) = await asyncio.gather(
                self.get_queries(
                    client,
                    access_token,
                    site_url,
                    start_date,
                    end_date,
                ),
                self.get_pages(
                    client,
                    access_token,
                    site_url,
                    start_date,
                    end_date,
                ),
                self.get_devices(
                    client,
                    access_token,
                    site_url,
                    start_date,
                    end_date,
                ),
                self.get_countries(
                    client,
                    access_token,
                    site_url,
                    start_date,
                    end_date,
                ),
                self.get_daily_performance(
                    client,
                    access_token,
                    site_url,
                    start_date,
                    end_date,
                ),
                self.get_sitemaps(
                    client,
                    access_token,
                    site_url,
                ),
            )

        return {
            "queries": queries,
            "pages": pages,
            "devices": devices,
            "countries": countries,
            "daily_performance": daily,
            "sitemaps": sitemaps,
        }

    async def query_pages(self, access_token, site_url, start_date, end_date):
        async with httpx.AsyncClient(timeout=12) as client:
            return await self._query(client, access_token, site_url, start_date, end_date, ["query", "page"], row_limit=50)
