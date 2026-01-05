import json
from typing import Any
from pydantic import ValidationError

from src.observability.tracing import log_event, Span
from src.llm.base import LLMClient, LLMRequest
from src.domain.prompt_store.prompt_store import PromptStore
from src.runtime.prompt_renderer import PromptRenderer
from src.runtime.workflows import IncidentPlan
from src.runtime.utils import normalize_usage

from src.core.errors import OrchestrationError

class LLMPlanGenerator:
    """
    Generates workflow plans using an LLM with structured JSON output.
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        prompt_store: PromptStore,
        renderer: PromptRenderer,
    ) -> None:
        self._llm = llm
        self._prompt_store = prompt_store
        self._renderer = renderer

    async def generate(
        self,
        *,
        trace_id: str,
        workflow: str,
        user_request: str,
        version: str,
        user_id: str | None,
    ) -> IncidentPlan:
        plan_span = Span(name='llm.plan', trace_id=trace_id)
        template = self._prompt_store.get_prompt(
            workflow=workflow,
            module="incident_plan",
            version=version,
        )
        schema = self._prompt_store.get_schema(
            workflow=workflow,
            module="incident_plan",
            version=version,
        )

        prompt = self._renderer.render(
            template,
            {"user_request": user_request},
        )

        resp = await self._llm.generate(
            LLMRequest(
                prompt=prompt,
                metadata={
                    "trace_id": trace_id,
                    "module": "incident_plan",
                    "version": version,
                    "workflow": workflow,
                    'phase': 'planning',
                },
                safety_identifier=user_id,
                json_schema=schema,
            )
        )

        plan_span.end()
        usage = (
            normalize_usage(getattr(resp, "usage", None))
            if "llm_plan_resp" in locals()
            else None
        )
        log_event(
            'span.end',
            trace_id=trace_id,
            span=plan_span,
            usage=usage,
        )

        try:
            obj = json.loads(resp.output_text)
            obj = self.normalize_plan(obj)
            return IncidentPlan.model_validate(obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            log_event(
                'workflow.plan.invalid',
                trace_id=trace_id,
                error=str(exc),
                raw_output=resp.output_text,
            )
            raise OrchestrationError(f"Invalid plan output: {exc}") from exc

    @staticmethod
    def normalize_plan(raw: dict[str, Any]) -> IncidentPlan:
        if "plan" in raw:
            steps = []
            for group in raw["plan"]:
                group_id = group.get("parallel_group")
                for s in group.get("steps", []):
                    steps.append(
                        {
                            "name": s["tool"],
                            "arguments": s["parameters"],
                            "parallel_group": group_id,
                        }
                    )
            return IncidentPlan(
                intent="incident_broadcast",
                steps=steps,
            )

        # already normalized
        return IncidentPlan.model_validate(raw)
