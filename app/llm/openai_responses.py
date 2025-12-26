"""OpenAI Responses API LLM adapter (HTTP-based).

Why HTTP directly?
- Keeps the adapter isolated and explicit.
- Avoids SDK drift in tutorial code.
- Makes it easier to mock with httpx transports.

Structured Outputs docs: use `text: { format: { type: "json_schema", strict: true, schema: ... } }`. :contentReference[oaicite:3]{index=3}
Responses API reference: request fields include `input`, `text`, and optional `safety_identifier`. :contentReference[oaicite:4]{index=4}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMUsage
from app.config import Settings


@dataclass(frozen=True)
class OpenAIResponsesConfig:
    """Configuration for the OpenAI Responses API adapter."""

    api_key: str
    base_url: str = 'https://api.openai.com/v1'
    model: str = 'gpt-4o-2024-08-06'
    temperature: float | None = None
    toolcall_envelope_schema: dict[str, Any] | None = None


class OpenAIResponsesLLMClient(LLMClient):
    """LLM adapter that calls OpenAI's Responses API."""

    def __init__(self, config: OpenAIResponsesConfig, client: httpx.AsyncClient | None = None) -> None:
        self._cfg = config
        self._client = client

    @staticmethod
    def from_env(
            *,
            model: str = 'gpt-4o-2024-08-06',
            schema: dict[str, Any] | None = None,
            temperature: float | None = None,
            settings: Settings | None = None,
    ) -> 'OpenAIResponsesLLMClient':
        api_key = settings.openai_api_key or os.environ.get('APP_OPENAI_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('APP_OPENAI_API_KEY is required to use OpenAIResponsesLLMClient.')
        cfg = OpenAIResponsesConfig(api_key=api_key, model=model, temperature=temperature)
        return OpenAIResponsesLLMClient(cfg)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        url = f'{self._cfg.base_url.rstrip("/")}/responses'
        headers = {
            'Authorization': f'Bearer {self._cfg.api_key}',
            'Content-Type': 'application/json',
        }

        body: dict[str, Any] = {
            'model': self._cfg.model,
            'input': request.prompt,
        }

        schema_name = (
            request.metadata.get("module")
            if request.metadata and "module" in request.metadata
            else "structured_output"
        )

        if request.json_schema is not None:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": request.json_schema,
                    "strict": True,
                }
            }

        if request.safety_identifier:
            body['safety_identifier'] = request.safety_identifier


        if self._client is not None:
            resp = await self._client.post(url, json=body, headers=headers, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                output_text=_extract_output_text(data),
                raw=data,
                usage=_extract_usage(data),
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                output_text=_extract_output_text(data),
                raw=data,
                usage=_extract_usage(data),
            )


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
            content = item.get('content')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') in ('output_text', 'text'):
                        text = c.get('text')
                        if isinstance(text, str) and text.strip():
                            return text

    # Some SDKs expose output_text; REST payloads may not. Keep a fallback.
    direct = payload.get('output_text')
    if isinstance(direct, str) and direct.strip():
        return direct

    raise ValueError('Unable to extract output text from Responses API payload.')

def _extract_usage(payload: dict[str, Any]) -> LLMUsage:
    usage = payload.get('usage')
    if not isinstance(usage, dict):
        return LLMUsage()

    # Responses API includes a usage object (token details). :contentReference[oaicite:5]{index=5}
    input_tokens = usage.get('input_tokens')
    output_tokens = usage.get('output_tokens')
    total_tokens = usage.get('total_tokens')

    return LLMUsage(
        input_tokens=int(input_tokens) if isinstance(input_tokens, int) else None,
        output_tokens=int(output_tokens) if isinstance(output_tokens, int) else None,
        total_tokens=int(total_tokens) if isinstance(total_tokens, int) else None,
    )
