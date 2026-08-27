# services/scheduler_service.py

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.oauth_account import OAuthAccount
from workers.daily_report_worker import generate_daily_report

logger = logging.getLogger(__name__)


class SchedulerService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_daily_reports(self) -> None:
        """
        Find all users and their verified Search Console sites,
        then publish one Celery task for each report.
        """

        logger.info("Starting daily report job queueing")

        users = await self._get_active_users()

        for user in users:

            oauth_account = await self._get_user_oauth_account(
                user.id
            )

            if not oauth_account:
                continue

            sites = await self._get_user_sites(
                oauth_account.credentials.access_token
            )

            for site_url in sites:

                # Publish task to Celery/Redis
                generate_daily_report.delay(
                    user_id=str(user.id),
                    site_url=site_url,
                )

                logger.info(
                    f"Queued daily report for "
                    f"{user.email} - {site_url}"
                )

        logger.info("Finished queueing daily report jobs")

    async def _get_active_users(self) -> list[User]:

        from models.oauth_credential import OAuthCredential

        query = (
            select(User)
            .join(
                OAuthAccount,
                User.id == OAuthAccount.user_id,
            )
            .join(
                OAuthCredential,
                OAuthAccount.id == OAuthCredential.oauth_account_id,
            )
            .where(
                OAuthCredential.access_token.isnot(None)
            )
            .distinct()
        )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def _get_user_oauth_account(
        self,
        user_id: str,
    ) -> OAuthAccount | None:

        from sqlalchemy.orm import selectinload

        query = (
            select(OAuthAccount)
            .options(
                selectinload(OAuthAccount.credentials)
            )
            .where(
                OAuthAccount.user_id == user_id
            )
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def _get_user_sites(
        self,
        access_token: str,
    ) -> list[str]:

        from services.search_console_service import (
            SearchConsoleService,
        )

        search_console_service = SearchConsoleService()

        try:
            sites_data = await search_console_service.list_sites(
                access_token
            )

            sites = []

            for entry in sites_data.get("siteEntry", []):

                permission = entry.get(
                    "permissionLevel",
                    "",
                )

                if permission in [
                    "siteOwner",
                    "siteFullUser",
                ]:
                    site_url = entry.get("siteUrl")

                    if site_url:
                        sites.append(site_url)

            return sites

        except Exception:
            logger.exception(
                "Failed to fetch Search Console sites"
            )
            return []