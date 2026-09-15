"""Run against a disposable database: SEO_TEST_DATABASE_NAME=seo_workspace_test_codex."""
import asyncio
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings
from models.seo_report import SEOReport
from models.seo_task import SEOTask
from models.user import User
from schemas.seo import AnalysisDraft, AnalysisRequest, CORE_STAGES
from services.seo_workspace_service import SEOWorkspaceService


def request(site="sc-domain:example.test", size="1-10"):
    return AnalysisRequest(site_url=site, website_number_of_pages=size,
                           website_type="saas", user_goal="increase organic traffic")


def draft(stage="technical-foundation", summary=""):
    return AnalysisDraft.model_validate({
        "report": "## Findings\nThe sampled page has no viewport meta tag.",
        "summary": summary,
        "tasks": [{
            "stage": stage, "title": "Add viewport metadata", "priority": "high",
            "scope": "https://example.test/", "evidence": "No viewport tag in the fetched HTML.",
            "why_it_matters": "Mobile browsers need the intended viewport size.",
            "manual_fix": "Add a viewport tag in the page head.",
            "agent_prompt": "Add a viewport meta tag without changing the page content.",
            "subtasks": ["Add viewport tag", "Check on a mobile viewport"],
        }],
    })


class SchemaTests(unittest.TestCase):
    def test_tasks_use_the_nine_core_stages(self):
        self.assertEqual(CORE_STAGES, [
            "technical-foundation", "crawlability", "rendering", "indexability",
            "on-page", "content", "search-intent", "semantic-seo", "ai-geo",
        ])
        with self.assertRaises(ValidationError):
            draft("local-seo")
        with self.assertRaises(ValidationError):
            draft("Invalid category!")
        with self.assertRaises(ValidationError):
            AnalysisRequest(**request().model_dump(exclude={"competitor_urls"}), competitor_urls=["file:///etc/passwd"])

    def test_invalid_model_output_does_not_become_a_report(self):
        from agents.weekly_agent import WeeklyAgent
        with self.assertRaises(ValidationError):
            WeeklyAgent._extract_analysis('This is a truncated report')
        with self.assertRaises(ValidationError):
            WeeklyAgent._extract_analysis('{"report": "fine", "tasks": [{"stage": "invented"}]}')
        with self.assertRaises(ValidationError):
            WeeklyAgent._extract_analysis('{"report": "fine"}')
        parsed = WeeklyAgent._extract_analysis('```json\n' + draft().model_dump_json() + '\n```')
        self.assertEqual(parsed.tasks[0].stage, "technical-foundation")
        self.assertEqual(parsed.summary, "")

    def test_task_status_cannot_be_supplied_by_model(self):
        payload = draft().model_dump()
        payload["tasks"][0]["completed_at"] = "2026-01-01"
        with self.assertRaises(ValidationError):
            AnalysisDraft.model_validate(payload)


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        name = os.environ.get("SEO_TEST_DATABASE_NAME", "")
        if not name.startswith("seo_workspace_test_"):
            raise unittest.SkipTest("Set SEO_TEST_DATABASE_NAME to a disposable seo_workspace_test_* database.")
        cls.url = make_url(settings.DATABASE_URL).set(database=name)
        env = {**os.environ, "DATABASE_URL": cls.url.render_as_string(hide_password=False), "DEBUG": "false"}
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True, capture_output=True)

    async def asyncSetUp(self):
        self.engine = create_async_engine(self.url, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        self.db = self.sessions()
        self.user = uuid4()
        self.other = uuid4()
        self.db.add_all([User(id=self.user, email=f"{self.user}@example.test"),
                         User(id=self.other, email=f"{self.other}@example.test")])
        await self.db.commit()
        self.service = SEOWorkspaceService(self.db)

    async def asyncTearDown(self):
        await self.db.rollback()
        await self.db.execute(delete(User).where(User.id.in_([self.user, self.other])))
        await self.db.commit()
        await self.db.close()
        await self.engine.dispose()

    async def saved_task(self, site="sc-domain:example.test"):
        run = await self.service.reserve_run(self.user, request(site))
        await self.service.finish_run(run.id, draft())
        tasks = await self.service.get_tasks(self.user, site)
        return run, tasks[0]

    async def test_report_without_summary_is_saved_and_survives_new_session(self):
        run, task = await self.saved_task()
        async with self.sessions() as another:
            workspace = await SEOWorkspaceService(another).workspace(self.user, request().site_url)
        self.assertEqual(workspace["latest_report"]["id"], str(run.id))
        self.assertEqual(workspace["latest_report"]["summary"], "")
        self.assertEqual(workspace["tasks"][0]["id"], str(task.id))
        self.assertEqual(workspace["pending_count"], 1)
        self.assertTrue(workspace["can_analyze"])

    async def test_completion_subtasks_reopen_and_idempotence(self):
        run, task = await self.saved_task()
        result = await self.service.set_completion(self.user, task.id, True, task.subtasks[0].id)
        self.assertIsNone(result["completed_at"])
        result = await self.service.set_completion(self.user, task.id, True, task.subtasks[1].id)
        self.assertIsNotNone(result["completed_at"])
        again = await self.service.set_completion(self.user, task.id, True)
        self.assertEqual(result["completed_at"], again["completed_at"])
        result = await self.service.set_completion(self.user, task.id, False, task.subtasks[0].id)
        self.assertIsNone(result["completed_at"])
        self.assertIsNotNone(result["subtasks"][1]["completed_at"])
        await self.service.set_completion(self.user, task.id, True)
        next_run = await self.service.reserve_run(self.user, request())
        self.assertEqual(next_run.stages, CORE_STAGES[1:5])
        await self.service.fail_run(next_run.id)
        self.assertEqual((await self.service.workspace(self.user, request().site_url))["latest_report"]["id"], str(run.id))

    async def test_pending_tasks_allow_new_analysis_and_duplicates_reuse_existing_work(self):
        await self.saved_task()
        run = await self.service.reserve_run(self.user, request())
        await self.service.finish_run(run.id, draft())
        self.assertEqual(len(await self.service.get_tasks(self.user, request().site_url)), 1)

    async def test_reviews_persist_without_changing_completion_and_reopen_resets_check(self):
        original, task = await self.saved_task()
        completed = await self.service.set_completion(self.user, task.id, True)
        run = await self.service.reserve_run(self.user, request())
        review = {"task_id": str(task.id), "title": task.title, "status": "not_observed",
                  "checked_at": datetime.now(timezone.utc).isoformat(), "detail": "Viewport is still absent."}
        await self.service.finish_run(run.id, draft(), {"reviews": [review], "pages": []})
        async with self.sessions() as another:
            workspace = await SEOWorkspaceService(another).workspace(self.user, request().site_url)
        self.assertEqual(len(workspace["tasks"]), 1)
        self.assertEqual(workspace["tasks"][0]["completed_at"], completed["completed_at"])
        self.assertEqual(workspace["tasks"][0]["review"]["status"], "not_observed")
        self.assertEqual(workspace["latest_report"]["evidence"]["reviews"], [review])
        self.assertEqual(original.evidence, {})
        await self.service.set_completion(self.user, task.id, False)
        self.assertEqual(task.review, {})
        self.assertEqual(run.evidence["reviews"], [review])

    async def test_foreign_review_cannot_be_saved(self):
        _, foreign = await self.saved_task("sc-domain:other.test")
        run = await self.service.reserve_run(self.user, request())
        with self.assertRaises(ValueError):
            await self.service.finish_run(run.id, draft(), {"reviews": [{"task_id": str(foreign.id)}]})
        await self.service.fail_run(run.id)

    async def test_core_stage_and_verification_survive_database_reload(self):
        payload = draft("technical-foundation").model_dump()
        payload["tasks"][0]["verification"] = {"field": "viewport", "expected": "width=device-width"}
        run = await self.service.reserve_run(self.user, request())
        await self.service.finish_run(run.id, AnalysisDraft.model_validate(payload), {"pages": [{"url": payload["tasks"][0]["scope"], "viewport": ""}]})
        async with self.sessions() as another:
            tasks = await SEOWorkspaceService(another).get_tasks(self.user, request().site_url)
        self.assertEqual(tasks[0].stage, "technical-foundation")
        self.assertEqual(tasks[0].verification["field"], "viewport")

    async def test_already_matching_check_does_not_create_repair_task(self):
        payload = draft().model_dump()
        payload["tasks"][0]["verification"] = {"field": "viewport", "expected": "width=device-width"}
        run = await self.service.reserve_run(self.user, request())
        await self.service.finish_run(run.id, AnalysisDraft.model_validate(payload), {"pages": [{"url": payload["tasks"][0]["scope"], "viewport": "width=device-width"}]})
        self.assertEqual(await self.service.get_tasks(self.user, request().site_url), [])

    async def test_real_agent_orchestration_with_mocked_network_and_model(self):
        import agents.weekly_agent as module
        from services.seo_review_service import SEOReviewService
        from services.scraper_service import ScraperService
        _, task = await self.saved_task()
        run = await self.service.reserve_run(self.user, request())
        run_id = run.id
        agent = module.WeeklyAgent.__new__(module.WeeklyAgent)
        agent.db = self.db
        agent.workspace_service = self.service
        agent.user_tool = AsyncMock(return_value={"access_token": "test-token"})
        agent.scraper = ScraperService()
        agent.scraper.scrape_from_sitemap = AsyncMock(return_value=[{"url": task.scope, "title": "Original"}])
        agent.scraper.scrape_page = AsyncMock(return_value={"url": "https://competitor.test/", "title": "Competitor"})
        search = AsyncMock()
        search.query_pages.return_value = {"rows": []}
        agent.reviewer = SEOReviewService(search)
        agent.model = None
        output = AsyncMock(return_value=AnalysisDraft(report="Reviewed saved work.", tasks=[]).model_dump_json())
        with patch.object(module, "collect_search_console_data", AsyncMock(return_value={})), \
             patch.object(module, "Agent", return_value=SimpleNamespace(invoke_async=output)):
            events = [event async for event in agent.run(user_id=str(self.user), run_id=run_id,
                      **request().model_dump(exclude={"competitor_urls"}), competitor_urls=["https://competitor.test/"])]
        self.assertEqual(events[-1], "Completed.")
        self.assertIn(task.scope, agent.scraper.scrape_from_sitemap.await_args.kwargs["priority_urls"])
        self.assertNotIn("test-token", output.await_args.args[0])
        workspace = await self.service.workspace(self.user, request().site_url)
        self.assertEqual(workspace["latest_report"]["evidence"]["reviews"][0]["status"], "manual_review")
        self.assertEqual(len(workspace["latest_report"]["evidence"]["competitors"]), 1)

    async def test_repeated_invalid_model_output_streams_error_and_preserves_saved_work(self):
        import agents.weekly_agent as module
        import api.routes.agents as routes
        from db.dbconfig import get_db
        from dependencies.auth import authenticate
        from services.seo_review_service import SEOReviewService

        _, task = await self.saved_task()
        await self.service.set_completion(self.user, task.id, True)
        before = await self.service.workspace(self.user, request().site_url)
        output = AsyncMock(side_effect=['{"report": "bad "quotes""}', '{"report":"text", "tasks":{}}'])

        def real_agent(db):
            agent = module.WeeklyAgent.__new__(module.WeeklyAgent)
            agent.db = db
            agent.workspace_service = SEOWorkspaceService(db)
            agent.user_tool = AsyncMock(return_value={"access_token": "test-token"})
            agent.scraper = SimpleNamespace(scrape_from_sitemap=AsyncMock(return_value=[]))
            search = AsyncMock()
            search.query_pages.return_value = {"rows": []}
            agent.reviewer = SEOReviewService(search)
            agent.model = None
            return agent

        async def db_dependency():
            async with self.sessions() as db:
                yield db

        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[get_db] = db_dependency
        app.dependency_overrides[authenticate] = lambda: {"sub": str(self.user)}
        with patch.object(routes, "AsyncSessionLocal", self.sessions), \
             patch.object(routes, "WeeklyAgent", side_effect=real_agent), \
             patch.object(routes.OAuthService, "get_valid_google_account", AsyncMock(return_value=SimpleNamespace(access_token="test-token"))), \
             patch.object(routes.SearchConsoleService, "list_sites", AsyncMock(return_value={"siteEntry": [{"siteUrl": request().site_url, "permissionLevel": "siteOwner"}]})), \
             patch.object(module, "collect_search_console_data", AsyncMock(return_value={})), \
             patch.object(module, "Agent", return_value=SimpleNamespace(invoke_async=output)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/agent/weekly", json=request().model_dump() | {"mode": "review"})
        self.assertEqual(response.status_code, 200)
        self.assertIn('"code": "invalid_analysis_output"', response.text)
        self.assertIn("after one formatting retry", response.text)
        self.assertNotIn('"type": "completed"', response.text)
        self.assertNotIn('"type": "result"', response.text)
        self.assertEqual(output.await_count, 2)
        async with self.sessions() as another:
            after = await SEOWorkspaceService(another).workspace(self.user, request().site_url)
            failed = await another.scalar(select(func.count()).select_from(SEOReport).where(
                SEOReport.user_id == self.user, SEOReport.status == "failed"))
        self.assertEqual(after["latest_report"], before["latest_report"])
        self.assertEqual(after["tasks"], before["tasks"])
        self.assertTrue(after["can_analyze"])
        self.assertEqual(failed, 1)

    async def test_tasks_and_history_are_scoped_to_user_and_exact_property(self):
        _, task = await self.saved_task()
        self.assertEqual((await self.service.workspace(self.other, request().site_url))["tasks"], [])
        self.assertIsNone((await self.service.workspace(self.user, "https://example.test/"))["latest_report"])
        with self.assertRaises(HTTPException) as error:
            await self.service.set_completion(self.other, task.id, True)
        self.assertEqual(error.exception.status_code, 404)

    async def test_failed_validation_leaves_no_tasks_or_completed_report(self):
        run = await self.service.reserve_run(self.user, request())
        invalid = draft("ai-geo")
        invalid.tasks[0].existing_task_id = str(uuid4())
        with self.assertRaises(ValueError):
            await self.service.finish_run(run.id, invalid)
        await self.service.fail_run(run.id)
        workspace = await self.service.workspace(self.user, request().site_url)
        self.assertIsNone(workspace["latest_report"])
        self.assertEqual(workspace["tasks"], [])
        self.assertTrue(workspace["can_analyze"])

    async def test_atomic_save_rolls_back_on_database_failure(self):
        run = await self.service.reserve_run(self.user, request())
        run_id = run.id
        with patch.object(self.db, "commit", side_effect=RuntimeError("injected write failure")):
            with self.assertRaises(RuntimeError):
                await self.service.finish_run(run_id, draft())
        await self.service.fail_run(run_id)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(SEOTask).where(SEOTask.report_id == run_id)), 0)
        self.assertIsNone((await self.service.workspace(self.user, request().site_url))["latest_report"])

    async def test_concurrent_starts_create_one_reservation(self):
        async def start():
            async with self.sessions() as db:
                try:
                    run = await SEOWorkspaceService(db).reserve_run(self.user, request())
                    return run.id
                except HTTPException as error:
                    await db.rollback()
                    return error.status_code
        results = await asyncio.gather(start(), start())
        self.assertEqual(results.count(409), 1)

    async def test_stale_reservation_recovers_without_advancing_stages(self):
        run = await self.service.reserve_run(self.user, request())
        run.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        await self.db.commit()
        replacement = await self.service.reserve_run(self.user, request())
        self.assertNotEqual(run.id, replacement.id)
        self.assertEqual(replacement.stages, [])
        with self.assertRaises(ValueError):
            await self.service.finish_run(run.id, draft())

    async def test_no_final_stage_and_empty_findings_are_valid(self):
        for stage in CORE_STAGES:
            run = await self.service.reserve_run(self.user, request())
            await self.service.finish_run(run.id, draft(stage))
        run = await self.service.reserve_run(self.user, request())
        await self.service.finish_run(run.id, AnalysisDraft(report="No supported new findings.", tasks=[]))
        workspace = await self.service.workspace(self.user, request().site_url)
        self.assertEqual(len(workspace["covered_stages"]), 9)
        self.assertTrue(workspace["can_analyze"])
        opportunity_run = await self.service.reserve_run(self.user, request())
        self.assertEqual(opportunity_run.stages, [])
        self.assertEqual(opportunity_run.preferences["phase"], "visibility-opportunities")

    async def test_http_history_task_updates_and_ownership(self):
        from api.routes.seo import router
        from dependencies.auth import authenticate
        from db.dbconfig import get_db
        app = FastAPI()
        app.include_router(router)

        async def db_dependency():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = db_dependency
        app.dependency_overrides[authenticate] = lambda: {"sub": str(self.user)}
        run, task = await self.saved_task()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/seo/workspace", params={"site_url": request().site_url})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            history = await client.get("/seo/reports", params={"site_url": request().site_url, "limit": 1})
            self.assertEqual(history.json()["reports"][0]["id"], str(run.id))
            bad = await client.patch(f"/seo/tasks/{task.id}", json={"completed": "yes"})
            self.assertEqual(bad.status_code, 422)
            good = await client.patch(f"/seo/tasks/{task.id}", json={"completed": True})
            self.assertIsNotNone(good.json()["completed_at"])
            app.dependency_overrides[authenticate] = lambda: {"sub": str(self.other)}
            self.assertEqual((await client.get(f"/seo/reports/{run.id}")).status_code, 404)
            self.assertEqual((await client.patch(f"/seo/tasks/{task.id}", json={"completed": False})).status_code, 404)

    async def test_analysis_endpoint_reserves_and_streams_saved_result(self):
        import api.routes.agents as routes
        from db.dbconfig import get_db
        from dependencies.auth import authenticate
        app = FastAPI()
        app.include_router(routes.router)

        async def db_dependency():
            async with self.sessions() as db:
                yield db

        class FakeAgent:
            def __init__(self, db):
                self.service = SEOWorkspaceService(db)

            async def run(self, **kwargs):
                yield "Fetching Search Console..."
                saved = await self.service.finish_run(kwargs["run_id"], draft())
                yield {"type": "result", "report_id": str(saved.id)}
                yield "Completed."

        app.dependency_overrides[get_db] = db_dependency
        app.dependency_overrides[authenticate] = lambda: {"sub": str(self.user)}
        with patch.object(routes, "AsyncSessionLocal", self.sessions), \
             patch.object(routes, "WeeklyAgent", FakeAgent), \
             patch.object(routes.OAuthService, "get_valid_google_account", AsyncMock(return_value=SimpleNamespace(access_token="test-token"))), \
             patch.object(routes.SearchConsoleService, "list_sites", AsyncMock(return_value={"siteEntry": [{"siteUrl": request().site_url, "permissionLevel": "siteOwner"}]})):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/agent/weekly", json=request().model_dump())
                self.assertEqual(response.status_code, 200)
                self.assertIn('"type": "result"', response.text)
                self.assertIn('"type": "completed"', response.text)
                self.assertNotIn('"type": "error"', response.text)
                self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
                repeated = await client.post("/agent/weekly", json=request().model_dump())
                self.assertEqual(repeated.status_code, 200)
                denied = await client.post("/agent/weekly", json=request("https://not-owned.test/").model_dump())
                self.assertEqual(denied.status_code, 403)
        self.assertEqual(len(await self.service.get_tasks(self.user, request().site_url)), 1)


class ZMigrationTests(unittest.TestCase):
    def test_upgrade_preserves_legacy_markdown_string(self):
        name = os.environ.get("SEO_TEST_DATABASE_NAME", "")
        if not name.startswith("seo_workspace_test_"):
            self.skipTest("A disposable SEO_TEST_DATABASE_NAME is required.")
        url = make_url(settings.DATABASE_URL).set(database=name)
        env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False), "DEBUG": "false"}

        def migrate(direction, revision):
            subprocess.run([sys.executable, "-m", "alembic", direction, revision], env=env, check=True, capture_output=True)

        migrate("downgrade", "a80ddacd7ea9")
        engine = create_engine(url)
        user_id, report_id = uuid4(), uuid4()
        original = "## Legacy report\nOriginal evidence with a canonical URL."
        try:
            with engine.begin() as connection:
                connection.execute(text("INSERT INTO users (id, email) VALUES (:id, :email)"), {"id": user_id, "email": f"{user_id}@example.test"})
                connection.execute(text("INSERT INTO seo_reports (id, user_id, site_url, report, summary) VALUES (:id, :user_id, 'sc-domain:example.test', to_jsonb(CAST(:report AS text)), 'Original summary')"),
                                   {"id": report_id, "user_id": user_id, "report": original})
            migrate("upgrade", "head")
            with engine.connect() as connection:
                row = connection.execute(text("SELECT report, status, stages, preferences, jsonb_typeof(report) FROM seo_reports WHERE id = :id"), {"id": report_id}).one()
                self.assertEqual(row.report, original)
                self.assertEqual(row.status, "completed")
                self.assertEqual(row.stages, [])
                self.assertEqual(row.preferences, {})
                self.assertEqual(row.jsonb_typeof, "string")
        finally:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
