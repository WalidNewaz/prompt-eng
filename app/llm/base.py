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
    """A request to generate model output.

    Attributes:
        prompt: Fully rendered prompt string (already version-selected and rendered).
        metadata: Opaque dict for tracing (prompt module/version, correlation IDs, etc.).
    """

    prompt: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    """A response from the model adapter.

    Attributes:
        output_text: The model output as text (often JSON text).
        raw: Provider-specific raw payload (kept for debugging/telemetry).
    """

    output_text: str
    raw: dict[str, Any]


class LLMClient(ABC):
    """Model inference adapter."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the model."""
        raise NotImplementedError
