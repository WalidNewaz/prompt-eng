"""End-to-end orchestration: prompt selection -> render -> LLM -> validate -> tool execute -> repair.

This is the "application brain". It is responsible for:
- choosing prompt module/version
- calling the model via LLMClient
- validating + parsing model output into a tool call envelope
- executing tools through the harness
- retrying with repair prompts on failures
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.base import LLMClient, LLMRequest
from app.prompts.loader import load_prompt
from app.runtime.harness import PromptToolHarness, ToolExecutionError
from app.runtime.renderer import PromptRenderer
from app.runtime.repair import build_repair_prompt
from app.schemas import validate_tool_call_payload


class OrchestrationError(RuntimeError):
    """Raised when orchestration fails after retries."""


class Orchestrator:
    """Coordinates prompt execution, validation, and repair."""

    def __init__(
        self,
        *,
        llm: LLMClient,
        harness: PromptToolHarness,
        renderer: PromptRenderer | None = None,
        max_retries: int = 1,
    ) -> None:
        self._llm = llm
        self._harness = harness
        self._renderer = renderer or PromptRenderer()
        self._max_retries = max_retries

    async def run_notification_router(
        self,
        *,
        user_request: str,
        prompt_version: str = 'v1',
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the notification routing flow end-to-end.

        Returns:
            Tool result payload from the internal tool service.
        """
        meta = metadata or {}
        template = load_prompt('notification', prompt_version)
        rendered = self._renderer.render(template, {'user_request': user_request})

        last_error: Exception | None = None
        current_prompt = rendered

        for attempt in range(self._max_retries + 1):
            llm_resp = await self._llm.generate(
                LLMRequest(
                    prompt=current_prompt,
                    metadata={
                        **meta,
                        'prompt_module': 'notification',
                        'prompt_version': prompt_version,
                        'attempt': attempt,
                    },
                )
            )

            try:
                tool_call_obj = _parse_json_object(llm_resp.output_text)
                _validated_tool_call = validate_tool_call_payload(tool_call_obj)
                # Execute side effects through the harness (schema-validated + real HTTP tool execution).
                return await self._harness.run_tool_call(tool_call_obj)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                current_prompt = build_repair_prompt(
                    original_prompt=rendered,
                    invalid_output_text=llm_resp.output_text,
                    error_message=str(exc),
                )
            except ToolExecutionError as exc:
                # Tool validation/execution failures are also repairable (wrong args, missing fields).
                last_error = exc
                if attempt >= self._max_retries:
                    break
                current_prompt = build_repair_prompt(
                    original_prompt=rendered,
                    invalid_output_text=llm_resp.output_text,
                    error_message=str(exc),
                )

        raise OrchestrationError(f'Orchestration failed after retries: {last_error}')


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a single JSON object from model output.

    We keep this strict by default. If you need to support code fences, you can extend it later.
    """
    stripped = text.strip()
    if stripped.startswith('```'):
        # Minimal fence stripping (common in LLM outputs)
        stripped = stripped.strip('`')
        stripped = stripped.replace('json', '', 1).strip()

    obj = json.loads(stripped)
    if not isinstance(obj, dict):
        raise ValueError('Model output must be a single JSON object.')
    return obj
