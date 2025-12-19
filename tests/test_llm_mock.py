from __future__ import annotations

import json

import pytest

from app.llm.base import LLMRequest
from app.llm.mock import MockLLMClient


@pytest.mark.asyncio
async def test_mock_llm_returns_json_text() -> None:
    llm = MockLLMClient(output={'name': 'send_email', 'arguments': {'to': 'a@b.com', 'subject': 'S', 'body': 'B'}})
    resp = await llm.generate(LLMRequest(prompt='X', metadata={}))
    payload = json.loads(resp.output_text)
    assert payload['name'] == 'send_email'
    assert 'arguments' in payload
