"""LLM adapters.

This package intentionally contains ONLY model inference adapters.

Rules:
- No tool execution here.
- No schema validation here.
- No retries/repair logic here.

Those belong in orchestration layers.
"""
# from .entities import (
#     LLMClient,
#     LLMRequest,
#     LLMResponse,
#     LLMUsage
# )
from .fake_llm_client import FakeLLMClient
from .openai_responses import OpenAIResponsesConfig, OpenAIResponsesLLMClient