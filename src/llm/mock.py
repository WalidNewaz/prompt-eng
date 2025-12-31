"""Mock LLM adapter.

Use this for:
- deterministic tests
- offline development
- unit tests for orchestration logic
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.base import LLMClient, LLMRequest, LLMResponse


class MockLLMClient(LLMClient):
    """A mock model that returns pre-canned outputs.

    Provide either:
    - a static dict payload (will be JSON-serialized), or
    - a callable that maps request -> dict payload.
    """

    def __init__(self, output: dict[str, Any] | None = None, fn: Any | None = None) -> None:
        self._output = output
        self._fn = fn

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any]
        if self._fn is not None:
            payload = self._fn(request)
        else:
            payload = self._output or {'name': 'request_missing_info', 'arguments': {}}

        return LLMResponse(output_text=json.dumps(payload), raw={'mock': True, 'payload': payload})
