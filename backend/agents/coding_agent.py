"""Independent SEO implementation agent.

The weekly agent creates evidence-backed tasks. This agent consumes one saved
task, works in a disposable Git worktree, validates the generated patch, and
commits only an approved HTML/content change to a task branch.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strands import Agent
from strands.models.litellm import LiteLLMModel

from core.config import settings
from models.seo_report import SEOReport
from models.seo_task import SEOTask
from models.site_settings import SiteSettings
from services.coding_agent_policy import CodingPolicyError, validate_patch
from services.coding_agent_sandbox import SandboxError, create_publish_sandbox, create_sandbox

logger = logging.getLogger(__name__)


class CodingAgentError(RuntimeError):
    pass


class CodingAgent:
    def __init__(self, db, sandbox_factory=None, patch_generator=None):
        self.db = db
        self.sandbox_factory = sandbox_factory or create_sandbox
        self.publish_sandbox_factory = create_publish_sandbox
        self.patch_generator = patch_generator or self._generate_patch

    async def run_task(self, task_id: UUID, user_id: UUID) -> dict:
        return await self.propose_task(task_id, user_id)

    async def propose_report_tasks(self, report_id: UUID, user_id: UUID) -> dict:
        """Generate reviewable sandbox proposals for new GitHub tasks in a report."""
        task_ids = (await self.db.scalars(
            select(SEOTask.id).join(SEOReport).where(
                SEOTask.report_id == report_id,
                SEOReport.user_id == user_id,
                SEOReport.status == "completed",
                SEOTask.target_platform == "github",
                SEOTask.completed_at.is_(None),
                SEOTask.implementation_status == "pending",
            ).order_by(SEOTask.position)
        )).all()
        summary = {
            "status": "completed",
            "attempted": len(task_ids),
            "proposed": 0,
            "blocked": 0,
            "failed": 0,
            "tasks": [],
        }
        for task_id in task_ids:
            try:
                result = await self.propose_task(task_id, user_id)
                status = result.get("status") or ("proposed" if result.get("approval_required") else "completed")
                summary[status if status in {"proposed", "blocked"} else "proposed"] += 1
                summary["tasks"].append({"task_id": str(task_id), "status": status})
            except (CodingPolicyError, SandboxError, CodingAgentError) as exc:
                summary["failed"] += 1
                summary["tasks"].append({"task_id": str(task_id), "status": "failed", "error": str(exc)})
                logger.warning("coding_agent.report_task_failed report_id=%s task_id=%s reason=%s", report_id, task_id, exc)
        if summary["failed"] or summary["blocked"]:
            summary["status"] = "partial" if summary["proposed"] else "failed"
        logger.info(
            "coding_agent.report_complete report_id=%s user_id=%s attempted=%s proposed=%s blocked=%s failed=%s",
            report_id, user_id, summary["attempted"], summary["proposed"], summary["blocked"], summary["failed"],
        )
        return summary

    async def propose_task(self, task_id: UUID, user_id: UUID) -> dict:
        logger.info(
            "coding_agent.propose.start task_id=%s user_id=%s environment=%s provider=%s",
            task_id, user_id, settings.CODING_AGENT_ENVIRONMENT, settings.CODING_AGENT_SANDBOX_PROVIDER,
        )
        task = await self._claim(task_id, user_id)
        settings_row = await self.db.scalar(select(SiteSettings).where(
            SiteSettings.user_id == user_id, SiteSettings.site_url == task.report.site_url,
        ))
        if not settings_row or not settings_row.github_owner or not settings_row.github_repo:
            return await self._block(task, "No GitHub repository is selected for this site.")
        repository_source = self._repository_source(settings_row)
        logger.info(
            "coding_agent.propose.repository task_id=%s repository=%s source_type=%s",
            task.id,
            self._repository_slug(settings_row),
            "local_fixture" if repository_source != f"https://github.com/{self._repository_slug(settings_row)}.git" else "github",
        )

        branch = self._branch_name(task)
        try:
            async with self.sandbox_factory(
                repository_source,
                settings.CODING_AGENT_GITHUB_BASE_BRANCH,
                token=settings.CODING_AGENT_GITHUB_TOKEN or None,
            ) as sandbox:
                await sandbox.verify_remote(settings_row.github_owner, settings_row.github_repo)
                files = await sandbox.files_for_context()
                allowed_paths = self._allowed_paths(files)
                if allowed_paths is not None:
                    files = {path: content for path, content in files.items() if path in allowed_paths}
                    if not files:
                        raise CodingAgentError("Test mode could not find an allowed homepage file in the repository.")
                patch = await self.patch_generator(task, files)
                policy = validate_patch(patch, allowed_paths=allowed_paths)
                result = await sandbox.apply_and_test(
                    patch, branch,
                    keep_preview=settings.CODING_AGENT_ENVIRONMENT.lower() == "test",
                )
                result["policy"] = policy
                result["approval_required"] = True
                result["environment"] = settings.CODING_AGENT_ENVIRONMENT.lower()
                result["repository"] = self._repository_slug(settings_row)
                task.implementation_status = "proposed"
                task.implementation_branch = branch
                task.implementation_diff = result["diff"]
                task.implementation_result = result
                task.implementation_error = ""
                task.implementation_completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                logger.info("coding_agent.proposed task_id=%s user_id=%s branch=%s", task.id, user_id, branch)
                return {"task_id": str(task.id), **result}
        except (CodingPolicyError, SandboxError, CodingAgentError) as exc:
            task.implementation_status = "blocked" if isinstance(exc, CodingPolicyError) else "failed"
            task.implementation_error = str(exc)
            task.implementation_completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.warning("coding_agent.rejected task_id=%s reason=%s", task.id, exc)
            raise
        except Exception as exc:
            task.implementation_status = "failed"
            task.implementation_error = "Unexpected coding-agent failure."
            task.implementation_completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.exception("coding_agent.unexpected_failure task_id=%s", task.id)
            raise CodingAgentError("The coding agent failed before it could safely finish.") from exc

    async def approve_task(self, task_id: UUID, user_id: UUID) -> dict:
        logger.info(
            "coding_agent.approve.start task_id=%s user_id=%s environment=%s",
            task_id, user_id, settings.CODING_AGENT_ENVIRONMENT,
        )
        task = await self._load_task(task_id, user_id)
        if task.implementation_status != "proposed" or not task.implementation_diff:
            raise CodingAgentError("Generate and review a proposed diff before approving this task.")
        settings_row = await self.db.scalar(select(SiteSettings).where(
            SiteSettings.user_id == user_id, SiteSettings.site_url == task.report.site_url,
        ))
        if not settings_row or not settings_row.github_owner or not settings_row.github_repo:
            raise CodingAgentError("No GitHub repository is selected for this site.")
        proposed_repository = (task.implementation_result or {}).get("repository", "")
        if proposed_repository and proposed_repository != self._repository_slug(settings_row):
            raise CodingAgentError("The selected repository changed after this diff was proposed. Generate a new diff before approval.")
        repository_source = self._repository_source(settings_row)

        branch = task.implementation_branch or self._branch_name(task)
        environment = settings.CODING_AGENT_ENVIRONMENT.lower()
        task.implementation_status = "running"
        await self.db.commit()
        try:
            factory = self.publish_sandbox_factory if environment == "production" else self.sandbox_factory
            async with factory(
                repository_source,
                settings.CODING_AGENT_GITHUB_BASE_BRANCH,
                token=settings.CODING_AGENT_GITHUB_TOKEN or None,
            ) as sandbox:
                await sandbox.verify_remote(settings_row.github_owner, settings_row.github_repo)
                if environment == "production":
                    result = await sandbox.publish_branch(
                        task.implementation_diff, branch, token=settings.CODING_AGENT_GITHUB_TOKEN or None,
                    )
                    pr = await self._create_pull_request(settings_row.github_owner, settings_row.github_repo, branch, task)
                    result["pull_request"] = pr
                    task.implementation_status = "pr_created"
                else:
                    result = await sandbox.apply_and_test(task.implementation_diff, branch, keep_preview=True)
                    result["approval_note"] = "Test mode keeps the approved branch local and does not push to GitHub."
                    task.implementation_status = "applied"
                result["environment"] = environment
                task.implementation_result = (task.implementation_result or {}) | result
                task.implementation_error = ""
                task.implementation_completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                logger.info("coding_agent.approved task_id=%s user_id=%s branch=%s environment=%s", task.id, user_id, branch, environment)
                return {"task_id": str(task.id), **result}
        except Exception as exc:
            task.implementation_status = "failed"
            task.implementation_error = str(exc) if isinstance(exc, (CodingAgentError, SandboxError)) else "Coding-agent approval failed."
            task.implementation_completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            if isinstance(exc, (CodingAgentError, SandboxError)):
                raise
            logger.exception("coding_agent.approval_unexpected_failure task_id=%s", task.id)
            raise CodingAgentError("The coding agent failed while creating the approved change.") from exc

    async def _claim(self, task_id, user_id):
        task = await self._load_task(task_id, user_id, for_update=True)
        if task.completed_at:
            raise CodingAgentError("Completed SEO tasks cannot be implemented.")
        if task.target_platform != "github":
            raise CodingAgentError("Only GitHub implementation tasks can be handled by the coding agent.")
        if task.implementation_status == "running":
            raise CodingAgentError("This task is already being implemented.")
        task.implementation_status = "running"
        task.implementation_attempts += 1
        task.implementation_started_at = datetime.now(timezone.utc)
        task.implementation_error = ""
        await self.db.commit()
        return task

    async def _load_task(self, task_id, user_id, for_update=False):
        query = select(SEOTask).join(SEOReport).where(
            SEOTask.id == task_id, SEOReport.user_id == user_id, SEOReport.status == "completed",
        ).options(selectinload(SEOTask.report))
        if for_update:
            query = query.with_for_update()
        task = await self.db.scalar(query)
        if task is None:
            raise CodingAgentError("SEO task not found for this user.")
        return task

    async def _block(self, task, message):
        task.implementation_status = "blocked"
        task.implementation_error = message
        task.implementation_completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {"task_id": str(task.id), "status": "blocked", "message": message}

    def _branch_name(self, task: SEOTask) -> str:
        return f"seo-agent/task-{str(task.id)[:12]}-a{task.implementation_attempts}"

    def _allowed_paths(self, files: dict[str, str]) -> set[str] | None:
        if settings.CODING_AGENT_ENVIRONMENT.lower() != "test":
            return None
        configured = {
            item.strip().replace("\\", "/").lstrip("./")
            for item in settings.CODING_AGENT_TEST_ALLOWED_PATHS.split(",")
            if item.strip()
        }
        return {path for path in files if path in configured}

    def _repository_source(self, settings_row: SiteSettings) -> str:
        """Resolve the target from this user's saved destination, never env."""
        if settings.CODING_AGENT_ENVIRONMENT.lower() == "test":
            local_checkout = settings.CODING_AGENT_TEST_REPOSITORY_ROOT.strip()
            if local_checkout:
                return local_checkout
        return f"https://github.com/{self._repository_slug(settings_row)}.git"

    @staticmethod
    def _repository_slug(settings_row: SiteSettings) -> str:
        return f"{settings_row.github_owner}/{settings_row.github_repo}"

    async def _create_pull_request(self, owner: str, repo: str, branch: str, task: SEOTask) -> dict:
        if not settings.CODING_AGENT_GITHUB_TOKEN:
            raise CodingAgentError("CODING_AGENT_GITHUB_TOKEN is required to create a production pull request.")
        payload = {
            "title": f"seo: {task.title[:180]}",
            "head": branch,
            "base": settings.CODING_AGENT_GITHUB_BASE_BRANCH,
            "body": (
                "SEO Agent approved change.\n\n"
                f"Task: {task.title}\n\n"
                f"Scope: {task.scope}\n\n"
                "The diff was generated and stored before approval; this PR was created only after approval."
            ),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {settings.CODING_AGENT_GITHUB_TOKEN}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json=payload,
            )
        if response.status_code >= 400:
            raise CodingAgentError(f"GitHub PR creation failed: {response.status_code} {response.text[:300]}")
        data = response.json()
        return {"number": data.get("number"), "url": data.get("html_url", ""), "state": data.get("state", "")}

    async def _generate_patch(self, task, files):
        model = LiteLLMModel(
            model_id=settings.LLM_MODEL_ID, stream=False,
            client_args={"api_key": settings.LLM_API_KEY, "num_retries": 0},
            params={"temperature": 0, "max_tokens": 3500, "reasoning_effort": "low"},
        )
        prompt = f"""You are a constrained SEO coding agent. Return ONLY a unified git diff.
You may modify only .html, .htm, .md, or .mdx files. Never touch scripts, CSS, config,
dependencies, tests, images, or build files. Make the smallest change that addresses the task.
Do not add JavaScript, CSS, event handlers, imports, variables, functions, or executable logic.
Task context: {json.dumps({key: getattr(task, key) for key in ('title', 'scope', 'evidence', 'why_it_matters', 'manual_fix', 'agent_prompt', 'verification')}, default=str)}
Repository files: {json.dumps(files)}
"""
        return str(await Agent(model=model, tools=[], callback_handler=None, retry_strategy=None).invoke_async(prompt)).strip()
