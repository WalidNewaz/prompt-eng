"""OpenAI Responses API LLM adapter (HTTP-based).

Why HTTP directly?
- Keeps the adapter isolated and explicit.
- Avoids SDK drift in tutorial code.
- Makes it easier to mock with httpx transports.

We use Structured Outputs (JSON Schema) to strongly bias the model toward valid JSON shapes. :contentReference[oaicite:1]{index=1}
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.base import LLMClient, LLMRequest, LLMResponse


@dataclass(frozen=True)
class OpenAIResponsesConfig:
    """Configuration for the OpenAI Responses API adapter."""

    api_key: str
    base_url: str = 'https://api.openai.com/v1'
    model: str = 'gpt-4.1-mini'
    # If you have a stricter JSON Schema, pass it here to enforce shape via Structured Outputs.
    # For this tutorial, we enforce the ToolCall envelope:
    # { "name": "...", "arguments": { ... } }
    toolcall_envelope_schema: dict[str, Any] | None = None


class OpenAIResponsesLLMClient(LLMClient):
    """LLM adapter that calls OpenAI's Responses API."""

    def __init__(self, config: OpenAIResponsesConfig, client: httpx.AsyncClient | None = None) -> None:
        self._cfg = config
        self._client = client

    @staticmethod
    def from_env(*, model: str = 'gpt-4.1-mini', schema: dict[str, Any] | None = None) -> 'OpenAIResponsesLLMClient':
        api_key = os.environ.get('OPENAI_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('OPENAI_API_KEY is required to use OpenAIResponsesLLMClient.')
        cfg = OpenAIResponsesConfig(api_key=api_key, model=model, toolcall_envelope_schema=schema)
        return OpenAIResponsesLLMClient(cfg)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        url = f'{self._cfg.base_url.rstrip("/")}/responses'
        headers = {
            'Authorization': f'Bearer {self._cfg.api_key}',
            'Content-Type': 'application/json',
        }

        # Responses API accepts "input". We send a single user-style content block containing the rendered prompt.
        # Structured Outputs: provide a JSON schema response format to enforce output shape. :contentReference[oaicite:2]{index=2}
        body: dict[str, Any] = {
            'model': self._cfg.model,
            'input': request.prompt,
        }

        if self._cfg.toolcall_envelope_schema is not None:
            body['response_format'] = {
                'type': 'json_schema',
                'json_schema': {
                    'name': 'tool_call_envelope',
                    'schema': self._cfg.toolcall_envelope_schema,
                    'strict': True,
                },
            }

        # Note: We intentionally keep tool/function calling out of this chapter’s adapter.
        # Our tutorial's "tool call" is a JSON object returned by the model.
        # Tool execution happens in the orchestrator/harness.

        if self._client is not None:
            resp = await self._client.post(url, json=body, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(output_text=_extract_output_text(data), raw=data)

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(output_text=_extract_output_text(data), raw=data)


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Extract text from a Responses API payload.

    The Responses API can return multiple output items. For this tutorial we look for the first
    text-like output and return it.
    """
    # Best-effort extraction that is resilient across minor payload changes.
    # If a deployment returns structured outputs in a different field, you can tighten this.
    output = payload.get('output')
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            # Common pattern: item has "content": [{"type":"output_text","text":"..."}]
            content = item.get('content')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') in ('output_text', 'text'):
                        text = c.get('text')
                        if isinstance(text, str) and text.strip():
                            return text
            # Fallback: some variants include a top-level "text"
            text = item.get('text')
            if isinstance(text, str) and text.strip():
                return text

    # Fallback: some payloads include "output_text" directly
    direct = payload.get('output_text')
    if isinstance(direct, str) and direct.strip():
        return direct

    raise ValueError('Unable to extract output text from Responses API payload.')
