from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.seo_report import SEOReport


class SEOReportsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_reports(
        self,
        user_id: str,
        site_url: str | None = None,
        limit: int = 10,
    ) -> list[SEOReport]:
        """
        Fetch previous SEO reports for a user.

        Only a bounded number of reports are returned. Results are ordered
        newest first.

        Args:
            user_id: User UUID.
            site_url: Optional Search Console property URL.
            limit: Maximum number of reports to return.

        Returns:
            List of SEOReport objects.
        """

        # Hard safety cap so the agent cannot request huge history.
        limit = min(max(limit, 1), 20)

        query = (
            select(SEOReport)
            .where(
                SEOReport.user_id == user_id,
            )
            .order_by(
                SEOReport.created_at.desc()
            )
            .limit(limit)
        )

        if site_url:
            query = query.where(
                SEOReport.site_url == site_url
            )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def create_report(
        self,
        user_id: str,
        site_url: str,
        report: str,
        summary: str,
    ) -> SEOReport:
        """
        Create and persist a new SEO report.

        Args:
            user_id: User UUID.
            site_url: Search Console property URL.
            report: Full generated SEO report.
            summary: Concise historical summary of the report.

        Returns:
            The newly created SEOReport object.
        """

        seo_report = SEOReport(
            user_id=user_id,
            site_url=site_url,
            report=report,
            summary=summary,
        )

        self.db.add(seo_report)

        await self.db.commit()

        await self.db.refresh(seo_report)

        return seo_report