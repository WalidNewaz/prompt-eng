from __future__ import annotations

import httpx
import pytest
import json
from httpx import MockTransport

from app.runtime.harness import PromptToolHarness
from app.runtime.orchestrator import Orchestrator
from app.tools.http_tool import HttpToolExecutor

from tests.fixtures.mock_llm_client import MockLLMClient
from tests.fixtures.tool_service_stub import tool_service_stub


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

    # transport = ASGITransport(app=app)
    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:
        executor = HttpToolExecutor(base_url="http://test", client=client)
        harness = PromptToolHarness(executor)
        orch = Orchestrator(llm=llm, harness=harness, max_retries=0)

        # Act
        result = await orch.run_notification_router(
            user_request="Notify #alerts that the build finished"
        )

    # Assert
    assert result["ok"] is True
    assert result["tool"] == "send_slack_message"
    assert "message_id" in result
