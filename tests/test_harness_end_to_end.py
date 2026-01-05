from __future__ import annotations

import json
import pytest
import httpx
from httpx import MockTransport

from src.runtime.harness import PromptToolHarness, ToolExecutionError
from src.runtime.orchestrator import Orchestrator
from src.tools.http_tool import HttpToolExecutor
from src.schemas import ToolName

from tests.fixtures.mock_llm_client import MockLLMClient
from tests.fixtures.tool_service_stub import tool_service_stub
from tests.fixtures.mock_policy_provider import MockPolicyProvider
from tests.fixtures.mock_prompt_store import MockPromptStore
from src.runtime.workflows import IncidentPlan
from tests.fixtures.fake_plan_generator import FakePlanGenerator
from tests.fixtures.mock_plan_executor import mock_plan_executor
from tests.fixtures.mock_prompt_renderer import mock_prompt_renderer
from tests.fixtures.mock_approval_gate import mock_approval_gate
from tests.fixtures.mock_summarizer import mock_summarizer

# ------------------------------------------------------------------------------
# Harness tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_harness_validates_and_executes_send_email() -> None:
    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://tool-service",
    ) as client:
        executor = HttpToolExecutor(base_url="http://tool-service", client=client)
        harness = PromptToolHarness(executor)

        tool_call = {
            "name": "send_email",
            "arguments": {
                "to": "dev@example.com",
                "subject": "Hi",
                "body": "Body",
            },
        }

        result = await harness.run_tool_call(tool_call)

    # The harness is the source of truth for the final response shape
    print(result)
    assert result["ok"] is True
    assert result["provider_message_id"].startswith("msg_")
    assert result["tool"] == "send_email"


@pytest.mark.anyio
async def test_harness_rejects_invalid_tool_args_before_execution() -> None:
    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://tool-service",
    ) as client:
        executor = HttpToolExecutor(base_url="http://tool-service", client=client)
        harness = PromptToolHarness(executor)

        tool_call = {
            "name": "send_email",
            "arguments": {
                "to": "not-an-email",
                "subject": "Hi",
                "body": "Body",
            },
        }

        with pytest.raises(ToolExecutionError) as exc:
            await harness.run_tool_call(tool_call)

    assert "Invalid tool call or arguments" in str(exc.value)


# ------------------------------------------------------------------------------
# Orchestrator test
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_orchestrator_routes_and_executes_tool_with_mock_llm() -> None:
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
        base_url="http://tool-service",
    ) as client:
        executor = HttpToolExecutor(base_url="http://tool-service", client=client)
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

        result = await orch.run_notification_router(
            user_request="Notify #alerts that the build finished"
        )

    assert result["ok"] is True
    assert result["tool"] == "send_slack_message"


# ------------------------------------------------------------------------------
# Security policy test
# ------------------------------------------------------------------------------

# def test_policy_rejects_unallowed_tool() -> None:
#     policy = SecurityPolicy(
#         allowed_tools={ToolName.SEND_EMAIL},
#         approval_required_tools=set(),
#     )
#
#     assert policy.is_allowed(ToolName.SEND_EMAIL) is True
#     assert policy.is_allowed(ToolName.SEND_SLACK_MESSAGE) is False


# ------------------------------------------------------------------------------
# HttpToolExecutor test
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_http_tool_executor_calls_fastapi_endpoint() -> None:
    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://tool-service",
    ) as client:
        executor = HttpToolExecutor(base_url="http://tool-service", client=client)

        result = await executor.execute(
            ToolName.SEND_SLACK_MESSAGE,
            {"channel": "#alerts", "text": "Hello", "urgency": "high", "message_id": "mock_message_id"},
        )

    # Executor returns the raw tool payload (no harness metadata)
    assert result["ok"] is True
    assert result["channel"] == "#alerts"
