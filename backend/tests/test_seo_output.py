import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from agents.output.seo_review import (
    AnalysisOutputError, INVALID_OUTPUT_MESSAGE, MAX_REPAIR_INPUT_CHARS,
    analysis_response_format, formatting_prompt,
)
from agents.prompts.seo_review import CONTRACT
from agents.weekly_agent import WeeklyAgent
from services.seo_task_generation_service import build_fallback_tasks
from schemas.seo import AnalysisDraft


VALID = AnalysisDraft(report="Observed HTML only; no supported new actions.", tasks=[]).model_dump_json()
MALFORMED = '{"report":"The page says "services"", "tasks":[]}'


class OutputTests(unittest.IsolatedAsyncioTestCase):
    def test_empty_model_output_gets_only_evidence_backed_fallback_tasks(self):
        tasks = build_fallback_tasks(
            [{"url": "https://example.com/", "status_code": 200, "title": "", "viewport": ""}],
            [],
        )
        self.assertEqual([task.title for task in tasks], ["Add a descriptive page title"])

    def test_strict_schema_keeps_all_task_fields_and_nullable_values(self):
        response_format = analysis_response_format()
        self.assertTrue(response_format["json_schema"]["strict"])
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(set(schema["required"]), {"report", "summary", "tasks"})
        task = schema["$defs"]["TaskDraft"]
        self.assertIn("title", task["properties"])
        self.assertEqual(set(task["required"]), set(task["properties"]))
        self.assertIn({"type": "null"}, task["properties"]["verification"]["anyOf"])
        self.assertIn({"type": "null"}, task["properties"]["existing_task_id"]["anyOf"])
        self.assertIn("Always include this key", task["properties"]["existing_task_id"]["description"])
        self.assertNotIn("default", task["properties"]["verification"])
        self.assertFalse(schema["additionalProperties"])
        for definition in schema["$defs"].values():
            self.assertFalse(definition["additionalProperties"])
        self.assertEqual(analysis_response_format(), response_format)

    def test_prompt_contract_requires_nullable_task_fields(self):
        self.assertIn("existing_task_id and verification", CONTRACT)
        self.assertIn("Set existing_task_id to null for new tasks", CONTRACT)
        self.assertIn("Set verification to null", CONTRACT)

    def test_model_request_enforces_schema_without_provider_streaming(self):
        agent = WeeklyAgent(None)
        request = agent.model.format_request([{"role": "user", "content": [{"text": "test"}]}])
        self.assertFalse(request["stream"])
        self.assertEqual(request["response_format"], analysis_response_format())
        self.assertEqual(agent.model.client_args["num_retries"], 0)

    async def run_output(self, responses):
        agent = WeeklyAgent.__new__(WeeklyAgent)
        agent.model = object()
        invoke = AsyncMock(side_effect=responses)
        with patch("agents.weekly_agent.Agent", return_value=SimpleNamespace(invoke_async=invoke)) as factory:
            result = await agent._validated_analysis("Original evidence prompt")
        return result, invoke, factory

    async def test_valid_first_response_has_no_retry(self):
        result, invoke, factory = await self.run_output([VALID])
        self.assertEqual(result.tasks, [])
        self.assertEqual(invoke.await_count, 1)
        self.assertIsNone(factory.call_args.kwargs["retry_strategy"])

    async def test_invalid_json_is_repaired_once_in_a_fresh_agent(self):
        result, invoke, factory = await self.run_output([MALFORMED, VALID])
        self.assertEqual(result.tasks, [])
        self.assertEqual(invoke.await_count, 2)
        self.assertEqual(factory.call_count, 2)
        repair = invoke.await_args_list[1].args[0]
        self.assertNotIn("Original evidence prompt", repair)
        data = json.loads(repair.split("\n", 1)[1])
        self.assertEqual(data["draft"], MALFORMED)
        self.assertEqual(data["validation_issues"][0]["type"], "json_invalid")
        self.assertLessEqual(len(repair), MAX_REPAIR_INPUT_CHARS)

    async def test_valid_json_with_wrong_schema_also_gets_one_retry(self):
        result, invoke, _ = await self.run_output(['{"report":"Findings", "tasks":"invalid"}', VALID])
        self.assertEqual(result.tasks, [])
        self.assertEqual(invoke.await_count, 2)

    async def test_second_invalid_response_stops_with_specific_error(self):
        agent = WeeklyAgent.__new__(WeeklyAgent)
        agent.model = None
        invoke = AsyncMock(side_effect=[MALFORMED, '{"report":"x","tasks":{}}', VALID])
        with patch("agents.weekly_agent.Agent", return_value=SimpleNamespace(invoke_async=invoke)):
            with self.assertRaisesRegex(AnalysisOutputError, "after one formatting retry") as error:
                await agent._validated_analysis("evidence")
        self.assertEqual(str(error.exception), INVALID_OUTPUT_MESSAGE)
        self.assertEqual(invoke.await_count, 2)

    async def test_upstream_failure_does_not_trigger_formatting_retry(self):
        agent = WeeklyAgent.__new__(WeeklyAgent)
        agent.model = None
        invoke = AsyncMock(side_effect=RuntimeError("provider unavailable"))
        with patch("agents.weekly_agent.Agent", return_value=SimpleNamespace(invoke_async=invoke)):
            with self.assertRaises(RuntimeError):
                await agent._validated_analysis("evidence")
        self.assertEqual(invoke.await_count, 1)

    async def test_formatting_retry_has_a_deadline(self):
        agent = WeeklyAgent.__new__(WeeklyAgent)
        agent.model = None
        async def slow(_):
            await asyncio.sleep(1)
            return VALID
        with patch("agents.weekly_agent.Agent", side_effect=[
            SimpleNamespace(invoke_async=AsyncMock(return_value=MALFORMED)),
            SimpleNamespace(invoke_async=slow),
        ]), patch("agents.weekly_agent.REPAIR_TIMEOUT_SECONDS", .01):
            with self.assertRaisesRegex(AnalysisOutputError, "timed out"):
                await agent._validated_analysis("evidence")

    def test_oversized_draft_is_not_silently_truncated(self):
        with self.assertRaises(ValidationError) as error:
            AnalysisDraft.model_validate_json(MALFORMED)
        with self.assertRaisesRegex(AnalysisOutputError, "too large"):
            formatting_prompt("x" * (MAX_REPAIR_INPUT_CHARS + 1), error.exception)


if __name__ == "__main__":
    unittest.main()
