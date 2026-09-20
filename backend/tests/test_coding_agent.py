import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from agents.coding_agent import CodingAgent, CodingAgentError
from agents.weekly_agent import WeeklyAgent
from core.config import settings


class CodingAgentReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_tasks_are_proposed_in_order_and_failures_do_not_stop_handoff(self):
        first_task_id = uuid4()
        second_task_id = uuid4()
        db = SimpleNamespace(
            scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [first_task_id, second_task_id])),
        )
        agent = CodingAgent.__new__(CodingAgent)
        agent.db = db
        agent.propose_task = AsyncMock(side_effect=[
            {"task_id": str(first_task_id), "approval_required": True},
            CodingAgentError("sandbox proposal failed"),
        ])

        result = await agent.propose_report_tasks(uuid4(), uuid4())

        self.assertEqual(result["attempted"], 2)
        self.assertEqual(result["proposed"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["status"], "partial")
        self.assertEqual([item["task_id"] for item in result["tasks"]], [str(first_task_id), str(second_task_id)])
        self.assertEqual(agent.propose_task.await_count, 2)

    async def test_weekly_handoff_runs_coding_agent_before_fastn(self):
        calls = []
        report_id = uuid4()
        user_id = uuid4()

        class FakeCodingAgent:
            def __init__(self, db):
                pass

            async def propose_report_tasks(self, received_report_id, received_user_id):
                calls.append(("coding", received_report_id, received_user_id))
                return {"status": "completed", "attempted": 1, "proposed": 1, "blocked": 0, "failed": 0}

        class FakeFastnTaskSyncService:
            def __init__(self, db):
                pass

            async def sync_report(self, received_report_id, received_user_id):
                calls.append(("fastn", received_report_id, received_user_id))
                return {"status": "completed"}

        agent = WeeklyAgent.__new__(WeeklyAgent)
        agent.db = object()
        with patch("agents.weekly_agent.CodingAgent", FakeCodingAgent), \
             patch("agents.weekly_agent.FastnTaskSyncService", FakeFastnTaskSyncService), \
             patch.object(settings, "CODING_AGENT_ENABLED", True):
            coding_result, fastn_result = await agent._complete_post_save_handoff(report_id, user_id)

        self.assertEqual([call[0] for call in calls], ["coding", "fastn"])
        self.assertEqual(coding_result["proposed"], 1)
        self.assertEqual(fastn_result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
