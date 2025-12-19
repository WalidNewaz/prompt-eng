"""End-to-end orchestration with retry + repair."""

from __future__ import annotations

from typing import Any

from app.runtime.harness import PromptToolHarness, ToolExecutionError
from app.runtime.repair import build_repair_prompt


class Orchestrator:
    """Coordinates prompt execution, validation, and repair."""

    def __init__(self, harness: PromptToolHarness, max_retries: int = 1) -> None:
        self._harness = harness
        self._max_retries = max_retries

    async def run(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await self._harness.run_tool_call(tool_call)
            except ToolExecutionError as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break

                # In real systems, you'd re-call the LLM with a repair prompt here.
                tool_call = {
                    'name': 'request_missing_info',
                    'arguments': {
                        'missing_fields': ['unknown'],
                        'question': str(exc),
                    },
                }

        raise RuntimeError(f'Orchestration failed after retries: {last_error}')
