"""Throwaway diagnostic: inspect the raw Search Console sitemaps payload."""

import asyncio
import json
from urllib.parse import quote

import httpx

from db.dbconfig import AsyncSessionLocal
from services.oauth_service import OAuthService

USER_ID = "fa3ed0bd-56f1-40ea-ad15-f6a1ae9528fe"
SITE_URL = "https://usman-is-a-dev.vercel.app/"


async def main():
    async with AsyncSessionLocal() as db:
        account = await OAuthService(db).get_google_account(user_id=USER_ID)
        token = account.credentials.access_token

    url = (
        "https://searchconsole.googleapis.com/webmasters/v3/sites/"
        f"{quote(SITE_URL, safe='')}/sitemaps"
    )

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers={"Authorization": f"Bearer {token}"})

    print("status:", res.status_code)
    print("body:", json.dumps(res.json(), indent=2)[:1500])


asyncio.run(main())
