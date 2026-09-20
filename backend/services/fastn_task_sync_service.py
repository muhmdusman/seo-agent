import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.seo_report import SEOReport
from models.seo_task import SEOTask
from services.fastn_workflow_service import FastnWorkflowService
from services.site_settings_service import SiteSettingsService, resolved_target_platform

logger = logging.getLogger(__name__)


class FastnTaskSyncService:
    def __init__(self, db, workflow=None):
        self.db = db
        self.workflow = workflow or FastnWorkflowService()

    async def sync_report(self, report_id, user_id=None):
        logger.info("fastn.task_sync.start report_id=%s requested_user_id=%s", report_id, user_id or "")
        query = select(SEOReport).where(SEOReport.id == report_id, SEOReport.status == "completed")
        if user_id is not None:
            query = query.where(SEOReport.user_id == user_id)
        report = await self.db.scalar(query)
        if report is None:
            logger.warning("fastn.task_sync.missing_report report_id=%s requested_user_id=%s", report_id, user_id or "")
            raise ValueError("Completed report not found.")

        tasks = (await self.db.scalars(
            select(SEOTask).where(SEOTask.report_id == report_id)
            .options(selectinload(SEOTask.subtasks)).order_by(SEOTask.position)
        )).all()
        if not tasks:
            logger.info("fastn.task_sync.no_tasks report_id=%s user_id=%s", report.id, report.user_id)
            return {"status": "NO_NEW_TASKS", "reportId": str(report.id)}

        settings = await SiteSettingsService(self.db).get(report.user_id, report.site_url)
        repo_configured = bool(settings.github_owner and settings.github_repo)
        logger.info(
            "fastn.task_sync.loaded report_id=%s user_id=%s site_url=%s task_count=%s repo=%s/%s spreadsheet_id=%s spreadsheet_name=%s",
            report.id,
            report.user_id,
            report.site_url,
            len(tasks),
            settings.github_owner,
            settings.github_repo,
            settings.google_spreadsheet_id,
            settings.google_spreadsheet_name,
        )

        payload = {
            "source": "backend_tasks",
            "reportId": str(report.id),
            "siteUrl": report.site_url,
            "github_owner": settings.github_owner,
            "github_repo": settings.github_repo,
            "google_spreadsheet_id": settings.google_spreadsheet_id,
            "google_spreadsheet_name": settings.google_spreadsheet_name,
            "spreadsheetId": settings.google_spreadsheet_id,
            "spreadsheetName": settings.google_spreadsheet_name,
            "tasks": [{
                "id": str(task.id),
                "title": task.title,
                "stage": task.stage,
                "priority": task.priority,
                "target_platform": resolved_target_platform({"target_platform": task.target_platform, "title": task.title,
                                                              "scope": task.scope, "evidence": task.evidence,
                                                              "why_it_matters": task.why_it_matters,
                                                              "manual_fix": task.manual_fix, "agent_prompt": task.agent_prompt},
                                                             repo_configured),
                "scope": task.scope,
                "evidence": task.evidence,
                "why_it_matters": task.why_it_matters,
                "manual_fix": task.manual_fix,
                "agent_prompt": task.agent_prompt,
                "subtasks": [subtask.title for subtask in task.subtasks],
                "verification": task.verification,
            } for task in tasks],
        }
        fastn_end_org_id = await self.workflow.resolve_customer_end_org(
            str(report.user_id)
        )

        logger.info(
            "fastn.task_sync.customer_resolved "
            "report_id=%s app_user_id=%s end_org_id=%s",
            report.id,
            report.user_id,
            fastn_end_org_id,
        )

        result = await self.workflow.execute(
            payload,
            tenant_id=fastn_end_org_id,
        )

        if isinstance(result, dict):
            result.setdefault(
                "selectedSheet",
                {
                    "spreadsheetId": settings.google_spreadsheet_id,
                    "spreadsheetName": settings.google_spreadsheet_name,
                },
            )

        logger.info(
            "fastn.task_sync.success "
            "report_id=%s end_org_id=%s result_keys=%s",
            report.id,
            fastn_end_org_id,
            sorted(result.keys()) if isinstance(result, dict) else [],
        )

        return result
