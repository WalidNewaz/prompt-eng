"""
This harness is intentionally simple but "real":
- Validates tool-call envelope
- Validates tool arguments (schema validation)
- Executes a real tool via FastAPI HTTP endpoints
- Validates tool results (schema validation)

In a production orchestrator, you would add:
- retries with repair prompts
- policy checks (authz, allowlists, rate limits)
- observability (structured logs, spans, metrics)
- prompt version selection
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import ValidationError

from src.schemas import ToolCall, ToolName, validate_tool_args, validate_tool_call_payload, validate_tool_result
from src.tools.base import ToolExecutor
from src.tools.http_tool import HttpToolExecutor


class ToolExecutionError(RuntimeError):
    """Raised when tool execution fails or returns invalid data."""


class PromptToolHarness:
    """Orchestrates tool-calling as a controlled execution pipeline."""

    def __init__(self, executor: ToolExecutor) -> None:
        self._executor = executor

    async def run_tool_call(self, raw_tool_call: dict[str, Any]) -> dict[str, Any]:
        """Validate and execute a tool call.

        Args:
            raw_tool_call: Tool call payload (e.g., from an LLM response).

        Returns:
            Validated tool result payload.

        Raises:
            ToolExecutionError: On validation issues or tool failures.
        """
        try:
            tool_call: ToolCall = validate_tool_call_payload(raw_tool_call)
            _validated_args_model = validate_tool_args(tool_call.name, tool_call.arguments)
        except ValidationError as exc:
            raise ToolExecutionError(f'Invalid tool call or arguments: {exc}') from exc

        try:
            result_payload = await self._executor.execute(tool_call.name, tool_call.arguments)
        except Exception as exc:  # noqa: BLE001 - boundary wrapper for tool failures
            raise ToolExecutionError(f'Tool execution failed: {exc}') from exc

        try:
            _validated_result_model = validate_tool_result(tool_call.name, result_payload)
        except ValidationError as exc:
            raise ToolExecutionError(f'Invalid tool result payload: {exc}') from exc

        return result_payload


def demo(base_url: str) -> None:
    """Run a tiny demo against a running FastAPI tool server."""
    executor = HttpToolExecutor(base_url=base_url)
    harness = PromptToolHarness(executor)

    async def _run() -> None:
        tool_calls = [
            {
                'name': ToolName.SEND_EMAIL.value,
                'arguments': {'to': 'dev@example.com', 'subject': 'Hello', 'body': 'This is a test.'},
            },
            {
                'name': ToolName.SEND_SLACK_MESSAGE.value,
                'arguments': {'channel': '#alerts', 'text': 'Deploy completed.', 'urgency': 'normal'},
            },
        ]

        for call in tool_calls:
            result = await harness.run_tool_call(call)
            print('TOOL RESULT:', result)

    asyncio.run(_run())
