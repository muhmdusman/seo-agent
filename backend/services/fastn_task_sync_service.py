from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.seo_report import SEOReport
from models.seo_task import SEOTask
from services.fastn_workflow_service import FastnWorkflowService
from services.site_settings_service import SiteSettingsService, resolved_target_platform


class FastnTaskSyncService:
    def __init__(self, db, workflow=None):
        self.db = db
        self.workflow = workflow or FastnWorkflowService()

    async def sync_report(self, report_id, user_id=None):
        query = select(SEOReport).where(SEOReport.id == report_id, SEOReport.status == "completed")
        if user_id is not None:
            query = query.where(SEOReport.user_id == user_id)
        report = await self.db.scalar(query)
        if report is None:
            raise ValueError("Completed report not found.")

        tasks = (await self.db.scalars(
            select(SEOTask).where(SEOTask.report_id == report_id)
            .options(selectinload(SEOTask.subtasks)).order_by(SEOTask.position)
        )).all()
        if not tasks:
            return {"status": "NO_NEW_TASKS", "reportId": str(report.id)}

        settings = await SiteSettingsService(self.db).get(report.user_id, report.site_url)
        repo_configured = bool(settings.github_owner and settings.github_repo)

        customer_id = str(report.user_id)
        if hasattr(self.workflow, "ensure_customer_org"):
            customer_id = await self.workflow.ensure_customer_org(
                customer_id, f"SEO Agent User {customer_id[:8]}"
            )

        return await self.workflow.execute({
            "source": "backend_tasks",
            "reportId": str(report.id),
            "siteUrl": report.site_url,
            "github_owner": settings.github_owner,
            "github_repo": settings.github_repo,
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
        }, tenant_id=customer_id)
