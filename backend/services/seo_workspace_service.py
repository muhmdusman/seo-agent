import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.orm import selectinload

from models.seo_report import SEOReport
from models.seo_task import SEOTask, SEOSubtask
from schemas.seo import AnalysisDraft, AnalysisRequest, next_stages
from services.seo_reports_service import SEOReportsService


PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "quick-win": 3}
RUN_TTL = timedelta(minutes=5)


def report_json(report):
    return {
        "id": str(report.id), "site_url": report.site_url,
        "report": report.report, "summary": report.summary,
        "created_at": report.created_at.isoformat(),
        "stages": report.stages, "preferences": report.preferences,
    }


def task_json(task):
    return {
        "id": str(task.id), "report_id": str(task.report_id),
        **{key: getattr(task, key) for key in (
            "stage", "title", "priority", "scope", "evidence",
            "why_it_matters", "manual_fix", "agent_prompt",
        )},
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "subtasks": [
            {"id": str(sub.id), "title": sub.title,
             "completed_at": sub.completed_at.isoformat() if sub.completed_at else None}
            for sub in task.subtasks
        ],
    }


class SEOWorkspaceService:
    def __init__(self, db):
        self.db = db

    async def _lock_site(self, user_id, site_url):
        # Transaction-scoped lock serializes short writes across API processes.
        key = int.from_bytes(hashlib.sha256(f"{user_id}:{site_url}".encode()).digest()[:8], "big", signed=True)
        await self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    async def get_tasks(self, user_id, site_url):
        result = await self.db.scalars(
            select(SEOTask).join(SEOReport, SEOReport.id == SEOTask.report_id)
            .where(SEOReport.user_id == user_id, SEOReport.site_url == site_url, SEOReport.status == "completed")
            .options(selectinload(SEOTask.subtasks))
            .order_by(SEOReport.created_at, SEOTask.position, SEOTask.id)
        )
        return sorted(result.all(), key=lambda task: (task.completed_at is not None, PRIORITIES[task.priority]))

    async def covered_stages(self, user_id, site_url):
        rows = await self.db.scalars(select(SEOReport.stages).where(
            SEOReport.user_id == user_id, SEOReport.site_url == site_url, SEOReport.status == "completed",
        ))
        return {stage for stages in rows for stage in stages}

    async def active_run(self, user_id, site_url):
        return await self.db.scalar(select(SEOReport.id).where(
            SEOReport.user_id == user_id, SEOReport.site_url == site_url,
            SEOReport.status == "running", SEOReport.created_at > datetime.now(timezone.utc) - RUN_TTL,
        ))

    async def workspace(self, user_id, site_url):
        reports = await SEOReportsService(self.db).get_user_reports(user_id, site_url, limit=1)
        latest = reports[0] if reports else None
        tasks = await self.get_tasks(user_id, site_url)
        covered = await self.covered_stages(user_id, site_url)
        pending = sum(task.completed_at is None for task in tasks)
        running = await self.active_run(user_id, site_url)
        return {
            "site_url": site_url,
            "latest_report": report_json(latest) if latest else None,
            "tasks": [task_json(task) for task in tasks],
            "covered_stages": sorted(covered), "pending_count": pending,
            "running": running is not None,
            "can_analyze": not pending and not running and len(covered) < 9,
        }

    async def reserve_run(self, user_id, request: AnalysisRequest):
        await self._lock_site(user_id, request.site_url)
        await self.db.execute(update(SEOReport).where(
            SEOReport.user_id == user_id, SEOReport.site_url == request.site_url,
            SEOReport.status == "running", SEOReport.created_at <= datetime.now(timezone.utc) - RUN_TTL,
        ).values(status="failed"))
        if await self.active_run(user_id, request.site_url):
            raise HTTPException(409, "An analysis is already running for this site.")
        tasks = await self.get_tasks(user_id, request.site_url)
        if any(task.completed_at is None for task in tasks):
            raise HTTPException(409, "Complete the existing tasks before starting the next analysis.")
        stages = next_stages(await self.covered_stages(user_id, request.site_url), request.website_number_of_pages)
        if not stages:
            raise HTTPException(409, "All nine stages have been covered.")
        run = SEOReport(
            user_id=user_id, site_url=request.site_url, report="", summary="",
            status="running", stages=stages,
            preferences=request.model_dump(exclude={"site_url"}),
        )
        self.db.add(run)
        await self.db.commit()
        return run

    async def finish_run(self, run_id, draft: AnalysisDraft):
        run = await self.db.scalar(select(SEOReport).where(SEOReport.id == run_id).with_for_update())
        if not run or run.status != "running":
            raise ValueError("This analysis reservation is no longer active.")
        if any(task.stage not in run.stages for task in draft.tasks):
            raise ValueError("The model returned tasks outside the assigned stages.")
        run.report = draft.report
        run.summary = draft.summary
        run.status = "completed"
        seen = set()
        for position, task in enumerate(draft.tasks):
            fingerprint = (task.stage, task.scope.strip(), task.title.casefold())
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            self.db.add(SEOTask(
                report_id=run.id, position=position,
                **task.model_dump(exclude={"subtasks"}),
                subtasks=[SEOSubtask(title=title, position=index) for index, title in enumerate(task.subtasks)],
            ))
        # A report and its task batch become visible together, or neither does.
        await self.db.commit()
        return run

    async def fail_run(self, run_id):
        await self.db.rollback()
        await self.db.execute(update(SEOReport).where(
            SEOReport.id == run_id, SEOReport.status == "running",
        ).values(status="failed"))
        await self.db.commit()

    async def set_completion(self, user_id, task_id: UUID, completed: bool, subtask_id: UUID | None = None):
        site_url = await self.db.scalar(select(SEOReport.site_url).join(
            SEOTask, SEOTask.report_id == SEOReport.id,
        ).where(SEOTask.id == task_id, SEOReport.user_id == user_id))
        if site_url is None:
            raise HTTPException(404, "Task not found.")
        await self._lock_site(user_id, site_url)
        if await self.active_run(user_id, site_url):
            raise HTTPException(409, "Wait for the current analysis before changing tasks.")
        task = await self.db.scalar(select(SEOTask).where(SEOTask.id == task_id)
                                    .options(selectinload(SEOTask.subtasks)).with_for_update())
        now = datetime.now(timezone.utc)
        if subtask_id is not None:
            subtask = next((sub for sub in task.subtasks if sub.id == subtask_id), None)
            if subtask is None:
                raise HTTPException(404, "Subtask not found.")
            subtask.completed_at = (subtask.completed_at or now) if completed else None
        else:
            for sub in task.subtasks:
                sub.completed_at = (sub.completed_at or now) if completed else None
        task.completed_at = (task.completed_at or now) if all(sub.completed_at for sub in task.subtasks) else None
        await self.db.commit()
        return task_json(task)

    async def agent_context(self, user_id, site_url):
        reports = await SEOReportsService(self.db).get_user_reports(user_id, site_url, limit=2)
        tasks = await self.get_tasks(user_id, site_url)
        return {
            "previous_reports": [{"date": report.created_at.isoformat(), "summary": (report.summary or report.report)[:600]} for report in reports],
            "pending_count": sum(task.completed_at is None for task in tasks),
            "completed_count": sum(task.completed_at is not None for task in tasks),
            "recent_tasks": [{"stage": task.stage, "title": task.title, "scope": task.scope,
                              "status": "user_completed" if task.completed_at else "pending"}
                             for task in tasks[-12:]],
        }
