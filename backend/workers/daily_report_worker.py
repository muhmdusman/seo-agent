"""
Celery worker for generating and delivering daily SEO reports.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from agents.daily_agent import DailyAgent
from core.celery_app import celery_app
from core.enums import JobStatus
from db.dbconfig import AsyncSessionLocal
from models.job import Job
from models.user import User
from services.email_service import email_service


# -------------------------------------------------------------------
# Windows asyncio compatibility
# -------------------------------------------------------------------
#
# Psycopg's async implementation cannot use Windows'
# ProactorEventLoop. Celery runs in a separate process from
# FastAPI, so we explicitly configure the event-loop policy here.
#
# This must happen before asyncio.run() creates the event loop.
#

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )


logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Celery task
# -------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="workers.daily_report_worker.generate_daily_report",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def generate_daily_report(
    self,
    job_id: str,
):
    """
    Celery entry point for a single daily SEO report job.

    Celery executes this synchronous function.

    The actual application logic is async, so we bridge
    into the async function using asyncio.run().
    """

    return asyncio.run(
        _process_daily_report(job_id)
    )


# -------------------------------------------------------------------
# Actual async job processing
# -------------------------------------------------------------------

async def _process_daily_report(
    job_id: str,
) -> None:
    """
    Process one daily SEO report job.

    Flow:

        queued
          ↓
       processing
          ↓
      DailyAgent
          ↓
        email
          ↓
       completed

    If anything fails:

        processing
            ↓
          failed
    """

    async with AsyncSessionLocal() as db:

        # -----------------------------------------------------------
        # 1. Fetch Job
        # -----------------------------------------------------------

        result = await db.execute(
            select(Job).where(
                Job.id == job_id
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            logger.error(
                f"Job {job_id} does not exist"
            )

            # There is nothing useful to retry if the
            # application-level Job doesn't exist.
            return

        logger.info(
            f"Starting job {job.id} "
            f"for user={job.user_id} "
            f"site={job.site_url}"
        )

        # -----------------------------------------------------------
        # 2. Mark job as processing
        # -----------------------------------------------------------

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        job.error_message = None

        await db.commit()

        try:

            # -------------------------------------------------------
            # 3. Fetch User
            # -------------------------------------------------------

            user_result = await db.execute(
                select(User).where(
                    User.id == job.user_id
                )
            )

            user = user_result.scalar_one_or_none()

            if user is None:
                raise ValueError(
                    f"User {job.user_id} "
                    f"does not exist"
                )

            # -------------------------------------------------------
            # 4. Create DailyAgent
            # -------------------------------------------------------

            daily_agent = DailyAgent(db)

            # -------------------------------------------------------
            # 5. Generate SEO report
            # -------------------------------------------------------

            logger.info(
                f"Generating report for "
                f"job={job.id} "
                f"site={job.site_url}"
            )

            report_content = (
                await daily_agent.generate_report(
                    user_id=str(job.user_id),
                    site_url=job.site_url,
                )
            )

            logger.info(
                f"Report generated for job={job.id}"
            )

            # -------------------------------------------------------
            # 6. Send email
            # -------------------------------------------------------

            success = await email_service.send_daily_report(
                user_email=user.email,
                user_name=(
                    user.username
                    or user.email.split("@")[0]
                ),
                site_url=job.site_url,
                report_content=report_content,
                report_date=datetime.now(
                    timezone.utc
                ).strftime("%B %d, %Y"),
            )

            if not success:
                raise RuntimeError(
                    f"Failed to send daily report "
                    f"email to {user.email}"
                )

            logger.info(
                f"Email sent successfully for "
                f"job={job.id}"
            )

            # -------------------------------------------------------
            # 7. Mark job as completed
            # -------------------------------------------------------

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(
                timezone.utc
            )
            job.error_message = None

            await db.commit()

            logger.info(
                f"Job {job.id} completed successfully"
            )

        except Exception as exc:

            # -------------------------------------------------------
            # 8. Mark job as failed
            # -------------------------------------------------------

            job.status = JobStatus.FAILED
            job.error_message = str(exc)

            await db.commit()

            logger.exception(
                f"Job {job.id} failed: {exc}"
            )

            # -------------------------------------------------------
            # 9. Re-raise
            # -------------------------------------------------------
            #
            # Celery must receive the exception so that its
            # autoretry mechanism knows the task failed.
            #

            raise