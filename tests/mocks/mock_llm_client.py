# ------------------------------------------------------------------------------
# Minimal, concrete MockLLMClient
# ------------------------------------------------------------------------------

from app.llm.base import LLMRequest, LLMResponse

class MockLLMClient:
    """
    Deterministic mock LLM client matching the real interface.
    """

    def __init__(self, *, output: str) -> None:
        self._output = output

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            output_text=self._output,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            model="mock-llm",
        )