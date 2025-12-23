"""LLM adapter interface.

This module defines the narrow contract used by orchestration code. The adapter is:
- swappable (OpenAI, Anthropic, local, etc.)
- mockable (deterministic tests)
- observable (metadata hooks)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    """
    A request to generate model output.

    Attributes:
        prompt: Fully rendered prompt string.
        metadata: Opaque dict for tracing.
        safety_identifier: Optional stable identifier for safety monitoring.
        json_schema: Optional JSON Schema enforcing output structure.
    """

    prompt: str
    metadata: dict[str, Any]
    safety_identifier: str | None = None
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMUsage:
    """Best-effort token usage summary (provider-dependent)."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class LLMResponse:
    """A response from the model adapter.

    Attributes:
        output_text: The model output as text (often JSON text).
        raw: Provider-specific raw payload (kept for debugging/telemetry).
        usage: Best-effort token usage
    """

    output_text: str
    raw: dict[str, Any]
    usage: LLMUsage = LLMUsage()


class LLMClient(ABC):
    """Model inference adapter."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the model."""
        raise NotImplementedError
