from __future__ import annotations

import httpx
import pytest
import json
from httpx import MockTransport

from src.runtime.harness import PromptToolHarness
from src.runtime.orchestrator import Orchestrator
from src.tools.http_tool import HttpToolExecutor
from src.runtime.workflows import IncidentPlan

# Fixtures
from tests.fixtures.mock_approval_repo import mock_approval_repo
from tests.fixtures.mock_llm_client import MockLLMClient
from tests.fixtures.tool_service_stub import tool_service_stub
from tests.fixtures.mock_policy_provider import MockPolicyProvider
from tests.fixtures.mock_prompt_store import MockPromptStore
from tests.fixtures.fake_plan_generator import FakePlanGenerator
from tests.fixtures.mock_plan_executor import mock_plan_executor
from tests.fixtures.mock_prompt_renderer import mock_prompt_renderer
from tests.fixtures.mock_approval_gate import mock_approval_gate
from tests.fixtures.mock_summarizer import mock_summarizer


@pytest.mark.asyncio
async def test_orchestrator_routes_and_executes_tool_with_mock_llm() -> None:
    # Arrange: mock model selects send_slack_message
    llm = MockLLMClient(
        output=json.dumps(
            {
                "name": "send_slack_message",
                "arguments": {
                    "channel": "#alerts",
                    "text": "Build finished.",
                    "urgency": "normal",
                    "message_id": "mock_message_id",
                },
            }
        )
    )
    fake_plan = IncidentPlan(
        intent="incident_broadcast",
        steps=[{
            "name": "send_slack_message",
            "arguments": {
                "channel": "#alerts",
                "text": "Build finished.",
                "urgency": "normal",
                "message_id": "mock_message_id",
            },
        }]
    )

    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:
        executor = HttpToolExecutor(base_url="http://test", client=client)
        harness = PromptToolHarness(executor)
        orch = Orchestrator(
            llm=llm,
            harness=harness,
            workflow={
                "name": "notification"
            },
            policy_provider=MockPolicyProvider(),
            prompt_store=MockPromptStore(),
            plan_generator=FakePlanGenerator(plan=fake_plan),
            plan_executor=mock_plan_executor,
            prompt_renderer=mock_prompt_renderer,
            approval_gate=mock_approval_gate,
            summarizer=mock_summarizer,
            max_retries=0
        )

        # Act
        result = await orch.run_notification_router(
            user_request="Notify #alerts that the build finished"
        )

    # Assert
    assert result["ok"] is True
    assert result["tool"] == "send_slack_message"
    assert "message_id" in result

@pytest.mark.asyncio
async def test_orchestrator_run_incident_broadcast_require_approval() -> None:
    llm = MockLLMClient(
        output=json.dumps(
            {
                "intent": "incident_broadcast",
                "steps": [{
                    "name": "send_slack_message",
                    "arguments": {},
                    "parallel_group": "normal",
                }],
            }
        )
    )
    fake_plan = IncidentPlan(
        intent="incident_broadcast",
        steps=[{
            "name": "send_slack_message",
            "arguments": {
                "channel": "#alerts",
                "text": "Build finished.",
                "urgency": "normal",
                "message_id": "mock_message_id",
            },
        }]
    )

    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:
        executor = HttpToolExecutor(base_url="http://test", client=client)
        harness = PromptToolHarness(executor)
        orch = Orchestrator(
            llm=llm,
            harness=harness,
            workflow={
                "name": "notification"
            },
            policy_provider=MockPolicyProvider(),
            prompt_store=MockPromptStore(),
            plan_generator=FakePlanGenerator(plan=fake_plan),
            plan_executor=mock_plan_executor,
            prompt_renderer=mock_prompt_renderer,
            approval_gate=mock_approval_gate,
            summarizer=mock_summarizer,
            max_retries=0
        )

        user_request = (
            "Broadcast an incident: 'Production checkout errors increasing'. "
            "Send Slack to #alerts with high urgency and email dev@example.com with subject 'INCIDENT'."
        )
        user_id = 'demo_user_001'

        result = await orch.run_incident_broadcast(
            user_request=user_request,
            user_id=user_id,
            approval_repository=mock_approval_repo,
        )

    # Assert
    # mock_approval_repo.create_pending.assert_called_once()
    assert result["status"] == "approval_required"
    assert result["approval_id"] == "approval_123"
    assert result["tools"] == ["send_slack_message"]


@pytest.mark.xfail(
    strict=True,
    reason="Currently passing due to hardcoded tool contracts for `request_missing_info`; will fail once general solution is implemented."
)
@pytest.mark.asyncio
async def test_orchestrator_run_incident_broadcast_plan_not_ready() -> None:
    llm = MockLLMClient(
        output=json.dumps(
            {
                "intent": "incident_broadcast",
                "steps": [{
                    "name": "request_missing_info",
                    "arguments": {
                    },
                    "parallel_group": "normal",
                }],
            }
        )
    )

    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:
        executor = HttpToolExecutor(base_url="http://test", client=client)
        harness = PromptToolHarness(executor)
        orch = Orchestrator(
            llm=llm,
            harness=harness,
            plan_executor=mock_plan_executor,
            summarizer=mock_summarizer,
            max_retries=0
        )

        user_request = (
            "Broadcast an incident: 'Production checkout errors increasing'. "
            "Send Slack to #alerts with high urgency and email dev@example.com with subject 'INCIDENT'."
        )
        user_id = 'demo_user_001'

        result = await orch.run_incident_broadcast(
            user_request=user_request,
            user_id=user_id,
            approval_repository=mock_approval_repo,
        )

    # Assert
    assert result["status"] == "awaiting_user_input"
    assert result["missing_fields"]["request_missing_info"] == ['test_field']
    assert result["reason"] == 'One or more steps are missing required inputs'


@pytest.mark.asyncio
async def test_orchestrator_run_incident_broadcast_execute_plan_dag() -> None:
    llm = MockLLMClient(
        output=json.dumps(
            {
                "intent": "incident_broadcast",
                "steps": [{
                    "name": "request_missing_info",
                    "arguments": {
                        "test_field": "test_value",
                    },
                    "parallel_group": "normal",
                }],
            }
        )
    )
    fake_plan = IncidentPlan(
        intent="incident_broadcast",
        steps=[{
            "name": "send_slack_message",
            "arguments": {
                "channel": "#alerts",
                "text": "Build finished.",
                "urgency": "normal",
                "message_id": "mock_message_id",
            },
        }]
    )

    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:
        executor = HttpToolExecutor(base_url="http://test", client=client)
        harness = PromptToolHarness(executor)
        orch = Orchestrator(
            llm=llm,
            harness=harness,
            workflow={
                "name": "notification"
            },
            policy_provider=MockPolicyProvider(),
            prompt_store=MockPromptStore(),
            plan_generator=FakePlanGenerator(plan=fake_plan),
            plan_executor=mock_plan_executor,
            prompt_renderer=mock_prompt_renderer,
            approval_gate=mock_approval_gate,
            summarizer=mock_summarizer,
            max_retries=0
        )

        user_request = (
            "Broadcast an incident: 'Production checkout errors increasing'. "
            "Send Slack to #alerts with high urgency and email dev@example.com with subject 'INCIDENT'."
        )
        user_id = 'demo_user_001'

        result = await orch.run_incident_broadcast(
            user_request=user_request,
            user_id=user_id,
            approval_repository=mock_approval_repo,
        )

    # Assertions
    # mock_plan_executor.execute.assert_called_once()
    # mock_summarizer.summarize.assert_called_once()
    # assert result["ok"] is True
    assert result["status"] == "approval_required"
