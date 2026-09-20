import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx

from core.config import settings
from schemas.fastn import FastnWorkflowExecuteRequest
from services.fastn_workflow_service import (
    FastnWorkflowConfigurationError,
    FastnWorkflowService,
)
from services.fastn_task_sync_service import FastnTaskSyncService
from services.site_settings_service import resolved_target_platform


class FastnWorkflowSchemaTests(unittest.TestCase):
    def test_implementation_tasks_route_to_github_when_repo_exists(self):
        self.assertEqual(resolved_target_platform({"target_platform": "manual_review", "title": "Add meta description", "manual_fix": "Edit the homepage template"}, True), "github")
        self.assertEqual(resolved_target_platform({"target_platform": "search_console", "title": "Submit sitemap"}, True), "search_console")
        self.assertEqual(resolved_target_platform({"target_platform": "manual_review", "title": "Review evidence"}, True), "manual_review")
    def test_input_payload_is_normalized_for_fastn(self):
        body = FastnWorkflowExecuteRequest.model_validate({
            "input": {"existing": True, "website_size": "301+"},
            "site_url": "sc-domain:example.test",
            "website_number_of_pages": "1-10",
            "website_type": "saas",
            "user_goal": "increase qualified traffic",
            "custom_flag": "keep-me",
        })

        self.assertEqual(body.workflow_input(), {
            "existing": True,
            "website_size": "1-10",
            "siteUrl": "sc-domain:example.test",
            "website_type": "saas",
            "user_goal": "increase qualified traffic",
            "custom_flag": "keep-me",
        })


class FastnWorkflowServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_key = settings.FASTN_API_KEY
        self.original_header = settings.FASTN_AUTH_HEADER
        self.original_scheme = settings.FASTN_AUTH_SCHEME

    async def asyncTearDown(self):
        settings.FASTN_API_KEY = self.original_key
        settings.FASTN_AUTH_HEADER = self.original_header
        settings.FASTN_AUTH_SCHEME = self.original_scheme

    async def test_missing_api_key_fails_before_network(self):
        settings.FASTN_API_KEY = ""

        with self.assertRaises(FastnWorkflowConfigurationError):
            await FastnWorkflowService().execute({})

    async def test_execute_posts_to_fastn_workflow_endpoint(self):
        settings.FASTN_API_KEY = "fsk_test_example"
        settings.FASTN_AUTH_HEADER = "Authorization"
        settings.FASTN_AUTH_SCHEME = "Bearer"
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers["Authorization"]
            seen["tenant"] = request.headers.get("x-fastn-space-tenantid")
            seen["test_mode"] = request.headers["X-fastn-Test-Mode"]
            seen["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"data": {"executionId": "exec_123", "status": "completed"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await FastnWorkflowService(
                workflow_id="wf_test",
                api_base_url="https://api.fastn.dev",
                client=client,
            ).execute({"siteUrl": "sc-domain:example.test"})

        self.assertEqual(seen["url"], "https://api.fastn.dev/api/v1/workflows/wf_test/execute")
        self.assertEqual(seen["authorization"], "Bearer fsk_test_example")
        self.assertIsNone(seen["tenant"])
        self.assertEqual(seen["test_mode"], "true")
        self.assertEqual(seen["body"], {"input": {"siteUrl": "sc-domain:example.test"}})
        self.assertEqual(result, {"data": {"executionId": "exec_123", "status": "completed"}})

    async def test_create_embed_token_uses_customer_header(self):
        settings.FASTN_API_KEY = "fsk_test_example"
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers["Authorization"]
            seen["customer"] = request.headers["x-org-id"]
            seen["test_mode"] = request.headers["X-fastn-Test-Mode"]
            return httpx.Response(200, json={"data": {"token": "emb_test", "endOrgId": "user-1", "expiresIn": 28800}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await FastnWorkflowService(api_base_url="https://api.fastn.dev", client=client).create_embed_token("user-1")

        self.assertEqual(seen["url"], "https://api.fastn.dev/api/v1/embed/token")
        self.assertEqual(seen["authorization"], "Bearer fsk_test_example")
        self.assertEqual(seen["customer"], "user-1")
        self.assertEqual(seen["test_mode"], "true")
        self.assertEqual(result["data"]["token"], "emb_test")

    async def test_ensure_customer_org_reuses_existing_reference(self):
        settings.FASTN_API_KEY = "fsk_test_example"
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.method)
            return httpx.Response(200, json={"data": [{"externalRef": "user-1", "orgId": "org-user-1"}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await FastnWorkflowService(
                api_base_url="https://api.fastn.dev", client=client,
            ).ensure_customer_org("user-1", "SEO Agent User")

        self.assertEqual(result, "org-user-1")
        self.assertEqual(calls, ["GET"])


class FastnTaskSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_report_sends_saved_tasks_with_stable_ids(self):
        report_id = uuid4()
        task_id = uuid4()
        user_id = uuid4()
        report = SimpleNamespace(id=report_id, user_id=user_id, site_url="sc-domain:example.test")
        site_settings = SimpleNamespace(github_owner="", github_repo="")
        task = SimpleNamespace(
            id=task_id, title="Add viewport", stage="technical-foundation",
            priority="high", target_platform="github", scope="https://example.test/",
            evidence="Viewport is absent", why_it_matters="Mobile layout is affected",
            manual_fix="Add viewport metadata", agent_prompt="Edit the page head",
            subtasks=[SimpleNamespace(title="Add tag")], verification=None,
        )
        db = SimpleNamespace(
            scalar=AsyncMock(side_effect=[report, site_settings]),
            scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [task])),
        )
        workflow = SimpleNamespace(execute=AsyncMock(return_value={"data": {"status": "queued"}}))

        result = await FastnTaskSyncService(db, workflow).sync_report(report_id, user_id)

        self.assertEqual(result["data"]["status"], "queued")
        payload = workflow.execute.await_args.args[0]
        self.assertEqual(payload["source"], "backend_tasks")
        self.assertEqual(payload["reportId"], str(report_id))
        self.assertEqual(payload["siteUrl"], "sc-domain:example.test")
        self.assertEqual(payload["tasks"][0]["id"], str(task_id))
        self.assertEqual(payload["tasks"][0]["target_platform"], "github")
        self.assertEqual(payload["tasks"][0]["subtasks"], ["Add tag"])
        self.assertEqual(workflow.execute.await_args.kwargs["tenant_id"], str(user_id))
