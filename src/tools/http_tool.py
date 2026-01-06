"""HTTP tool executor that calls a FastAPI tool service."""

from __future__ import annotations

from typing import Any

import httpx

from src.tools.schemas import ToolName
from src.tools.base import ToolExecutor


class HttpToolExecutor(ToolExecutor):
    """Execute tools by calling an HTTP service.

    This is the pattern most companies use internally:
    - LLM chooses a tool + args
    - the orchestrator calls an internal service
    - the internal service performs side effects (email, Slack, ticketing, etc.)
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        """Create an HTTP tool executor.

        Args:
            base_url: Base URL of the internal tool service (e.g. http://tool-svc:8001).
            client: Optional injected httpx client for testing / transport control.
        """
        self._base_url = base_url.rstrip('/')
        self._client = client

    async def execute(self, tool_name: ToolName, args: dict[str, Any]) -> dict[str, Any]:
        endpoint = self._endpoint_for(tool_name)
        url = f'{self._base_url}{endpoint}'

        if self._client is not None:
            resp = await self._client.post(url, json=args, timeout=120.0)
            resp.raise_for_status()
            return resp.json()

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=args, timeout=120.0)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _endpoint_for(tool_name: ToolName) -> str:
        if tool_name == ToolName.SEND_SLACK_MESSAGE:
            return '/tools/send-slack'
        if tool_name == ToolName.SEND_EMAIL:
            return '/tools/send-email'
        if tool_name == ToolName.REQUEST_MISSING_INFO:
            return '/tools/request-missing-info'
        raise ValueError(f'Unsupported tool name: {tool_name}')
