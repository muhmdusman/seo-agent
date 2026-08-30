from strands import tool

from services.seo_reports_service import SEOReportsService


def create_historical_reports_tool(db):

    service = SEOReportsService(db)

    @tool
    async def get_historical_seo_reports(
        user_id: str,
        site_url: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Retrieve previous SEO report summaries for a user's website.

        Use this tool when historical context is useful for comparing
        the current SEO state against previous analyses.

        Only report summaries are returned, never full reports.

        Args:
            user_id: User UUID.
            site_url: Website being analyzed.
            limit: Maximum number of historical summaries to retrieve.
                   Maximum allowed is 10.
        """

        limit = min(max(limit, 1), 10)

        reports = await service.get_user_reports(
            user_id=user_id,
            site_url=site_url,
            limit=limit,
        )

        return [
            {
                "report_id": str(report.id),
                "site_url": report.site_url,
                "created_at": report.created_at.isoformat(),
                "summary": report.summary,
            }
            for report in reports
        ]

    return get_historical_seo_reports