# services/scheduler_service.py

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.job import Job
from models.user import User
from models.oauth_account import OAuthAccount
from core.enums import JobStatus
from workers.daily_report_worker import generate_daily_report

logger = logging.getLogger(__name__)


class SchedulerService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_daily_reports(self) -> None:
        """
        Discover today's daily report jobs.

        PostgreSQL stores the job.
        Celery only receives the job ID and processes it asynchronously.
        """

        logger.info("Starting daily report job queueing")

        users = await self._get_active_users()

        for user in users:

            oauth_account = await self._get_user_oauth_account(
                user.id
            )

            if not oauth_account:
                logger.warning(
                    f"No OAuth account for user {user.id}"
                )
                continue

            sites = await self._get_user_sites(
                oauth_account.credentials.access_token
            )

            for site_url in sites:

                # --------------------------------------------------
                # 1. Create persistent job in PostgreSQL
                # --------------------------------------------------

                job = Job(
                    user_id=user.id,
                    site_url=site_url,
                    status=JobStatus.QUEUED,
                )

                self.db.add(job)

                # Generate/persist the UUID before sending to Celery
                await self.db.flush()

                job_id = str(job.id)

                # --------------------------------------------------
                # 2. Commit the job
                # --------------------------------------------------

                await self.db.commit()

                # --------------------------------------------------
                # 3. Publish ONLY job_id to Celery
                # --------------------------------------------------

                generate_daily_report.delay(
                    job_id=job_id
                )

                logger.info(
                    f"Queued daily report job={job_id} "
                    f"user={user.email} "
                    f"site={site_url}"
                )

        logger.info(
            "Finished queueing daily report jobs"
        )

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
                OAuthAccount.id
                == OAuthCredential.oauth_account_id,
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
                selectinload(
                    OAuthAccount.credentials
                )
            )
            .where(
                OAuthAccount.user_id == user_id,
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

            for entry in sites_data.get(
                "siteEntry",
                [],
            ):

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