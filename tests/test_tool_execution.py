from __future__ import annotations

import httpx
import pytest
from httpx import MockTransport

from app.schemas import ToolName
from app.tools.http_tool import HttpToolExecutor

from tests.fixtures.tool_service_stub import tool_service_stub


@pytest.mark.anyio
async def test_http_tool_executor_calls_fastapi_endpoint() -> None:
    # Arrange
    transport = MockTransport(tool_service_stub)

    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        executor = HttpToolExecutor(base_url='http://test', client=client)

        # Act
        result = await executor.execute(
            ToolName.SEND_SLACK_MESSAGE,
            {'channel': '#alerts', 'text': 'Hello', 'urgency': 'high', "message_id": "mock_message_id"},
        )

    # Assert
    assert result['ok'] is True
    assert result['tool'] == 'send_slack_message'
    assert isinstance(result['message_id'], str)
    assert len(result['message_id']) > 0
