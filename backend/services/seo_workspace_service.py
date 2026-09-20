import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.orm import selectinload

from core.seo_framework import SEO_STAGES, next_stage_bundle
from models.seo_report import SEOReport
from models.seo_task import SEOTask, SEOSubtask
from schemas.seo import AnalysisDraft, AnalysisRequest
from services.seo_reports_service import SEOReportsService
from services.seo_review_service import check_page
from services.site_settings_service import SiteSettingsService, resolved_target_platform


PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "quick-win": 3}
RUN_TTL = timedelta(minutes=5)


def report_json(report):
    return {
        "id": str(report.id), "site_url": report.site_url,
        "report": report.report, "summary": report.summary,
        "created_at": report.created_at.isoformat(),
        "stages": report.stages, "preferences": report.preferences,
        "evidence": report.evidence,
    }


def task_json(task):
    return {
        "id": str(task.id), "report_id": str(task.report_id),
        **{key: getattr(task, key) for key in (
            "stage", "title", "priority", "target_platform", "scope", "evidence",
            "why_it_matters", "manual_fix", "agent_prompt",
        )},
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "verification": task.verification, "review": task.review,
        "implementation": {
            "status": task.implementation_status,
            "attempts": task.implementation_attempts,
            "branch": task.implementation_branch,
            "diff": task.implementation_diff,
            "result": task.implementation_result,
            "error": task.implementation_error,
            "started_at": task.implementation_started_at.isoformat() if task.implementation_started_at else None,
            "completed_at": task.implementation_completed_at.isoformat() if task.implementation_completed_at else None,
        },
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
        return {stage for stages in rows for stage in stages if stage in SEO_STAGES}

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
        preferences = latest.preferences if latest else {}
        remaining = [stage for stage in SEO_STAGES if stage not in covered]
        phase = preferences.get("phase", "framework") if latest else "framework"
        if not remaining and phase == "framework":
            # The next run should continue with visibility work even when the
            # latest completed report was the final framework bundle.
            phase = "visibility-opportunities"
        pending = sum(task.completed_at is None for task in tasks)
        running = await self.active_run(user_id, site_url)
        return {
            "site_url": site_url,
            "latest_report": report_json(latest) if latest else None,
            "tasks": [task_json(task) for task in tasks],
            "covered_stages": sorted(covered), "pending_count": pending,
            "running": running is not None,
            "can_analyze": not running,
            "framework_complete": not remaining,
            "next_stages": next_stage_bundle(covered, preferences.get("website_number_of_pages", "1-10")) if remaining else [],
            "phase": phase,
            "next_review_at": min(
                (task.completed_at + timedelta(days=10) for task in tasks
                 if task.completed_at and (task.review or {}).get("performance", {}).get("status") != "compared"),
                default=latest.created_at + timedelta(days=7) if latest else None,
            ),
        }

    async def reserve_run(self, user_id, request: AnalysisRequest):
        await self._lock_site(user_id, request.site_url)
        await self.db.execute(update(SEOReport).where(
            SEOReport.user_id == user_id, SEOReport.site_url == request.site_url,
            SEOReport.status == "running", SEOReport.created_at <= datetime.now(timezone.utc) - RUN_TTL,
        ).values(status="failed"))
        if await self.active_run(user_id, request.site_url):
            raise HTTPException(409, "An analysis is already running for this site.")
        covered = await self.covered_stages(user_id, request.site_url)
        assigned_stages = next_stage_bundle(covered, request.website_number_of_pages)
        phase = "framework" if assigned_stages else ("review-results" if request.mode == "review" else "visibility-opportunities")
        run = SEOReport(
            user_id=user_id, site_url=request.site_url, report="", summary="",
            status="running", stages=assigned_stages,
            preferences={
                **request.model_dump(mode="json", exclude={"site_url", "audit_snapshot"}),
                "phase": phase, "assigned_stages": assigned_stages,
            },
        )
        self.db.add(run)
        await self.db.commit()
        return run

    async def finish_run(self, run_id, draft: AnalysisDraft, evidence: dict | None = None):
        run = await self.db.scalar(select(SEOReport).where(SEOReport.id == run_id).with_for_update())
        if not run or run.status != "running":
            raise ValueError("This analysis reservation is no longer active.")
        existing = await self.get_tasks(run.user_id, run.site_url)
        existing_by_id = {str(task.id): task for task in existing}
        if any(task.existing_task_id and task.existing_task_id not in existing_by_id for task in draft.tasks):
            raise ValueError("Referenced task does not belong to this workspace.")
        observations = evidence or {}
        if any(review["task_id"] not in existing_by_id for review in observations.get("reviews", [])):
            raise ValueError("Reviewed task does not belong to this workspace.")
        phase = (run.preferences or {}).get("phase", "framework")
        allowed_stages = set(run.stages) if phase == "framework" else set(SEO_STAGES)
        if any(task.stage not in allowed_stages for task in draft.tasks):
            raise ValueError("The model returned a task outside the active SEO framework stage bundle.")
        run.report = draft.report
        run.summary = draft.summary
        task_stats = {"candidate": len(draft.tasks), "created": 0, "reused": 0, "already_observed": 0}
        run.evidence = {**observations, "task_generation": task_stats}
        run.status = "completed"
        site_settings = await SiteSettingsService(self.db).get(run.user_id, run.site_url)
        repo_configured = bool(site_settings.github_owner and site_settings.github_repo)
        # Preserve task identity and the user's checkbox state across reviews.
        def fingerprint(task):
            check = task.verification
            field = check.get("field") if isinstance(check, dict) else getattr(check, "field", None)
            expected = check.get("expected") if isinstance(check, dict) else getattr(check, "expected", None)
            identity = f"check:{field}:{expected}" if field else " ".join(task.title.casefold().split())
            return task.scope.strip(), identity

        seen = {fingerprint(task) for task in existing}
        observed_pages = {page.get("url"): page for page in observations.get("pages", [])}
        for review in observations.get("reviews", []):
            existing_by_id[review["task_id"]].review = review
        for position, task in enumerate(draft.tasks):
            key = fingerprint(task)
            if task.existing_task_id:
                task_stats["reused"] += 1
                continue
            if key in seen:
                task_stats["reused"] += 1
                continue
            if task.verification and check_page(task.verification.model_dump(), observed_pages.get(task.scope))[0] == "observed":
                task_stats["already_observed"] += 1
                continue
            seen.add(key)
            task_stats["created"] += 1
            task_data = task.model_dump(exclude={"subtasks", "existing_task_id"})
            task_data["target_platform"] = resolved_target_platform(task_data, repo_configured)
            self.db.add(SEOTask(
                report_id=run.id, position=position,
                **task_data,
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
        # Reopening starts a new implementation cycle; retain old evidence in reports.
        if task.completed_at is None:
            task.review = {}
        await self.db.commit()
        return task_json(task)

    async def agent_context(self, user_id, site_url):
        reports = await SEOReportsService(self.db).get_user_reports(user_id, site_url, limit=2)
        tasks = await self.get_tasks(user_id, site_url)
        covered = await self.covered_stages(user_id, site_url)
        # Rotate checks by oldest observation so a bounded run does not starve older tasks.
        review_queue = sorted(tasks, key=lambda task: ((task.review or {}).get("checked_at", ""), str(task.id)))
        return {
            "previous_reports": [{"date": report.created_at.isoformat(), "summary": (report.summary or report.report)[:600]} for report in reports],
            "pending_count": sum(task.completed_at is None for task in tasks),
            "completed_count": sum(task.completed_at is not None for task in tasks),
            "covered_stages": sorted(covered),
            "recent_tasks": [{"id": str(task.id), "stage": task.stage, "title": task.title, "scope": task.scope,
                              "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                              "verification": task.verification,
                              "last_measurement_at": (task.review or {}).get("performance", {}).get("checked_at", ""),
                              "status": "user_completed" if task.completed_at else "pending"}
                             for task in review_queue[:12]],
            "tasks_omitted": max(0, len(tasks) - 12),
            "previous_pages": (reports[0].evidence or {}).get("pages", []) if reports else [],
        }
