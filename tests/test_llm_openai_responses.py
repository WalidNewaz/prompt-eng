from __future__ import annotations

import httpx
import pytest

from src.infrastructure.llm import (
    LLMRequest,
    OpenAIResponsesConfig,
    OpenAIResponsesLLMClient
)

@pytest.mark.asyncio
async def test_openai_responses_adapter_extracts_output_text() -> None:
    # Arrange: mock Responses API payload with a typical output_text item.
    fake_payload = {
        "id": "resp_test",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "{\"name\":\"send_email\",\"arguments\":{}}"}],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/responses")
        return httpx.Response(200, json=fake_payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.openai.com") as client:
        cfg = OpenAIResponsesConfig(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4.1-mini",
            toolcall_envelope_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["name", "arguments"],
                "additionalProperties": False,
            },
        )
        llm = OpenAIResponsesLLMClient(cfg, client=client)

        # Act
        resp = await llm.generate(LLMRequest(prompt="PROMPT", metadata={"x": 1}))

    # Assert
    assert resp.output_text.strip().startswith("{")
    assert resp.raw["id"] == "resp_test"
