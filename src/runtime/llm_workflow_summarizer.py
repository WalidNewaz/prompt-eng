from typing import Any
import json
from pathlib import Path

from pydantic import ValidationError

from src.llm.base import LLMClient, LLMRequest
from src.observability.tracing import Span, log_event
from src.prompts.loader import load_prompt
from .prompt_renderer import PromptRenderer
from .workflows import (
    ExecutionRecord,
    IncidentPlan,
    IncidentSummary,
)
from .prompt_utils import load_json_schema
from .utils import normalize_usage
from src.core.errors import OrchestrationError

BASE_DIR = Path(__file__).resolve().parents[1]

class LLMWorkflowSummarizer:
    """
    Produces workflow summaries using an LLM and a structured JSON schema.
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        renderer: PromptRenderer,
        summary_version: str = "v1",
    ) -> None:
        self._llm = llm
        self._renderer = renderer
        self._summary_version = summary_version


    async def summarize(
        self,
        *,
        trace_id: str,
        records: list[ExecutionRecord],
        safe_user_request: str,
        plan: IncidentPlan,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        summary_span = Span(name="llm.summarize", trace_id=trace_id)

        template = load_prompt("incident_summary", self._summary_version)

        tool_outcomes_json = json.dumps(
            [r.model_dump() for r in records],
            ensure_ascii=False,
        )

        prompt = self._renderer.render(
            template,
            {
                "user_request": safe_user_request,
                "tool_outcomes_json": tool_outcomes_json,
            },
        )

        try:
            schema = load_json_schema(
                f"{BASE_DIR}/prompts/incident_summary/{self._summary_version}/schema.json"
            )

            resp = await self._llm.generate(
                LLMRequest(
                    prompt=prompt,
                    metadata={
                        "trace_id": trace_id,
                        "module": "incident_summary",
                        "version": self._summary_version,
                    },
                    safety_identifier=user_id,
                    json_schema=schema,
                )
            )
        finally:
            summary_span.end()
            log_event(
                "span.end",
                trace_id=trace_id,
                span=summary_span,
                usage=normalize_usage(getattr(resp, "usage", None))
                if "resp" in locals()
                else None,
            )

        try:
            summary_obj = json.loads(resp.output_text.strip())
            summary = IncidentSummary.model_validate(summary_obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            log_event(
                "workflow.summary.invalid",
                trace_id=trace_id,
                error=str(exc),
                raw_output=resp.output_text,
            )
            raise OrchestrationError(
                f"Summary produced invalid JSON: {exc}"
            ) from exc

        return {
            "trace_id": trace_id,
            "plan": plan.model_dump(),
            "tool_execution_records": [r.model_dump() for r in records],
            "summary": summary.model_dump(),
        }


