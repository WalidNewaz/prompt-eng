from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from app.schemas import ToolName
from app.server.fastapi_tool_server import app
from app.tools.http_tool import HttpToolExecutor


@pytest.mark.anyio
async def test_http_tool_executor_calls_fastapi_endpoint() -> None:
    # Arrange
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        executor = HttpToolExecutor(base_url='http://test', client=client)

        # Act
        result = await executor.execute(
            ToolName.SEND_SLACK_MESSAGE,
            {'channel': '#alerts', 'text': 'Hello', 'urgency': 'high'},
        )

    # Assert
    assert result['ok'] is True
    assert result['tool'] == 'send_slack_message'
    assert isinstance(result['message_id'], str)
    assert len(result['message_id']) > 0
