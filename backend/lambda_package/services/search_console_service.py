from datetime import date
from urllib.parse import quote

import asyncio
import httpx


class SearchConsoleService:

    BASE_URL = "https://searchconsole.googleapis.com/webmasters/v3"

    def _headers(
        self,
        access_token: str,
    ):

        return {
            "Authorization": f"Bearer {access_token}",
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
        print({ "queries": queries,
                    "pages": pages,
                    "devices": devices,
                    "countries": countries,
                    "daily_performance": daily,
                    "sitemaps": sitemaps})
        return {
            "queries": queries,
            "pages": pages,
            "devices": devices,
            "countries": countries,
            "daily_performance": daily,
            "sitemaps": sitemaps,
        }