from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from app.runtime.harness import PromptToolHarness, ToolExecutionError
from app.server.fastapi_tool_server import app
from app.tools.http_tool import HttpToolExecutor


@pytest.mark.anyio
async def test_harness_validates_and_executes_send_email() -> None:
    # Arrange
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        executor = HttpToolExecutor(base_url='http://test', client=client)
        harness = PromptToolHarness(executor)

        tool_call = {
            'name': 'send_email',
            'arguments': {'to': 'dev@example.com', 'subject': 'Hi', 'body': 'Body'},
        }

        # Act
        result = await harness.run_tool_call(tool_call)

    # Assert
    assert result['ok'] is True
    assert result['tool'] == 'send_email'
    assert result['provider_message_id'].startswith('msg_')


@pytest.mark.anyio
async def test_harness_rejects_invalid_tool_args_before_execution() -> None:
    # Arrange
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        executor = HttpToolExecutor(base_url='http://test', client=client)
        harness = PromptToolHarness(executor)

        tool_call = {
            'name': 'send_email',
            'arguments': {'to': 'not-an-email', 'subject': 'Hi', 'body': 'Body'},
        }

        # Act / Assert
        with pytest.raises(ToolExecutionError) as exc:
            await harness.run_tool_call(tool_call)

    assert 'Invalid tool call or arguments' in str(exc.value)
