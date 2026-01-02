"""End-to-end orchestration: prompt selection -> render -> LLM -> validate -> tool execute -> repair.

This is the "application brain". It is responsible for:
- choosing prompt module/version
- calling the model via LLMClient
- validating + parsing model output into a tool call envelope
- executing tools through the harness
- retrying with repair prompts on failures
- Multi-step chain: Plan -> Execute (DAG) -> Summarize
- Observability: trace + spans + timing
- Security: tool allowlists, sanitization

LLM: Responses API only (via adapter).
Structured Outputs: use `text.format` json_schema. :contentReference[oaicite:6]{index=6}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import re

from pydantic import ValidationError

from src.core.errors import LLMParseError, OrchestrationError
from src.llm.base import LLMClient, LLMRequest
from src.observability.tracing import Span, log_event, new_trace_id
from src.prompts.loader import load_prompt
from src.runtime.harness import PromptToolHarness, ToolExecutionError
from src.runtime.renderer import PromptRenderer
from src.runtime.workflows import IncidentPlan
from src.schemas import validate_tool_call_payload
from src.security.policy import (
    build_policy_for_workflow,
    sanitize_user_text,
    evaluate_plan,
)
from src.security.policy_decision import PolicyOutcome
from src.runtime.repair import build_repair_prompt
from src.domain.approval.repository import ApprovalRequestRepositoryProtocol
from src.runtime.readiness import evaluate_readiness, ReadinessOutcome
from .utils import normalize_usage
from .plan_executor import PlanExecutor
from .prompt_utils import load_json_schema
from .workflow_summarizer import WorkflowSummarizer
from .llm_workflow_summarizer import LLMWorkflowSummarizer


BASE_DIR = Path(__file__).resolve().parents[1]


class Orchestrator:
    """Coordinates prompt execution, validation, and repair."""

    def __init__(
        self,
        *,
        llm: LLMClient,
        harness: PromptToolHarness,
        plan_executor: PlanExecutor | None = None,
        renderer: PromptRenderer | None = None,
        summarizer: WorkflowSummarizer | None = None,
        max_retries: int = 1,
    ) -> None:
        self._llm = llm
        self._harness = harness
        self._plan_executor = plan_executor or PlanExecutor(harness=harness)
        self._renderer = renderer or PromptRenderer()
        self._summarizer = summarizer or LLMWorkflowSummarizer(
            llm=llm,
            renderer=self._renderer,
        )
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

    async def run_incident_broadcast(
            self,
            *,
            user_request: str,
            tool_plan_version: str = 'v1',
            summary_version: str = 'v1',
            user_id: str | None = None,
            approval_repository: ApprovalRequestRepositoryProtocol | None = None,
    ) -> dict[str, Any]:
        """Plan -> Execute (DAG) -> Summarize.

        Returns a dict containing:
        - trace_id
        - plan
        - tool_execution_records
        - summary
        """
        trace_id = new_trace_id()
        policy = build_policy_for_workflow('incident_broadcast')

        safe_user_request = sanitize_user_text(user_request)
        log_event('workflow.start', trace_id=trace_id, workflow='incident_broadcast')

        # -------------------------
        # 1) PLAN (LLM -> IncidentPlan JSON)
        # -------------------------
        plan_span = Span(name='llm.plan', trace_id=trace_id)
        plan_template = load_prompt('incident_plan', tool_plan_version)
        plan_prompt = self._renderer.render(plan_template, {'user_request': safe_user_request})

        # Structured output schema for planner
        plan_schema = load_json_schema(f'{BASE_DIR}/prompts/incident_plan/{tool_plan_version}/schema.json')

        try:
            llm_plan_resp = await self._llm.generate(
                LLMRequest(
                    prompt=plan_prompt,
                    metadata={
                        'trace_id': trace_id,
                        'module': 'incident_plan',
                        'version': tool_plan_version,
                        'workflow': 'incident_broadcast',
                        'phase': 'planning',
                    },
                    safety_identifier=user_id,
                    json_schema = plan_schema,
                ),
            )
        finally:
            plan_span.end()
            usage = (
                normalize_usage(getattr(llm_plan_resp, "usage", None))
                if "llm_plan_resp" in locals()
                else None
            )
            log_event(
                'span.end',
                trace_id=trace_id,
                span=plan_span,
                usage=usage,
            )

        # Parse + validate plan (Pydantic)
        try:
            plan_obj = json.loads(llm_plan_resp.output_text)
            plan = normalize_plan(plan_obj)
            plan = IncidentPlan.model_validate(plan_obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            log_event(
                'workflow.plan.invalid',
                trace_id=trace_id,
                error=str(exc),
                raw_output=llm_plan_resp.output_text,
            )
            raise OrchestrationError(f'Planner produced invalid plan: {exc}') from exc

        # -------------------------
        # POLICY CHECK
        # -------------------------
        # Security: allowlist tools in plan
        decisions = evaluate_plan(policy, [s.name for s in plan.steps])
        for d in decisions:
            if d.outcome == PolicyOutcome.DENY:
                log_event(
                    "workflow.policy.denied",
                    trace_id=trace_id,
                    tool=d.tool.value,
                    reason=d.reason,
                )
                raise OrchestrationError(d.reason)

        # -------------------------
        # APPROVAL GATE
        # -------------------------
        approval_needed = [
            d for d in decisions
            if d.outcome == PolicyOutcome.REQUIRE_APPROVAL
        ]

        if approval_needed:
            approval_id = approval_repository.create_pending(
                trace_id=trace_id,
                workflow="incident_broadcast",
                tool_name=", ".join(d.tool.value for d in approval_needed),
                safe_user_request=safe_user_request,
                plan=plan.model_dump(),
                reason="One or more tools require approval",
                requested_by=user_id,
            )

            log_event(
                "workflow.awaiting_approval",
                trace_id=trace_id,
                approval_id=approval_id,
                tools=[d.tool.value for d in approval_needed],
            )

            return {
                "status": "approval_required",
                "approval_id": approval_id,
                "tools": [d.tool.value for d in approval_needed],
            }


        log_event(
             'workflow.plan.ok',
            trace_id=trace_id,
            steps=len(plan.steps),
            plan=plan.model_dump()
        )

        # -------------------------
        # READINESS CHECK
        # -------------------------
        readiness = evaluate_readiness(plan)

        if readiness.outcome == ReadinessOutcome.NEEDS_INPUT:
            log_event(
                "workflow.needs_input",
                trace_id=trace_id,
                missing=readiness.missing_fields,
            )

            return {
                "status": "awaiting_user_input",
                "missing_fields": readiness.missing_fields,
                "reason": readiness.reason,
            }

        # -------------------------
        # 2) EXECUTE (DAG: parallel groups + join)
        # -------------------------
        exec_span = Span(name='tools.execute_dag', trace_id=trace_id)
        exec_span.attributes['step_count'] = len(plan.steps)

        try:
            records = await self._plan_executor.execute(
                trace_id=trace_id,
                steps=plan.steps,
                policy=policy
            )
        finally:
            exec_span.end()
            log_event('span.end', trace_id=trace_id, span=exec_span)

        # -------------------------
        # 3) SUMMARIZE (LLM -> IncidentSummary JSON)
        # -------------------------
        result = await self._summarizer.summarize(
            trace_id=trace_id,
            records=records,
            safe_user_request=safe_user_request,
            plan=plan,
            user_id=user_id,
        )

        return result


    async def resume_approved_workflow(
            self,
            *,
            approval_id: str,
            approved_by: str,
            approval_repository: ApprovalRequestRepositoryProtocol | None = None,
    ) -> dict[str, Any]:
        approval = approval_repository.get(approval_id)

        if approval.status != "PENDING":
            raise OrchestrationError("Approval already decided")

        approval_repository.mark_approved(approval_id, approved_by)

        plan = IncidentPlan.model_validate(approval.plan)

        log_event(
            "workflow.approved",
            trace_id=approval.trace_id,
            approved_by=approved_by,
        )

        # -------------------------
        # READINESS CHECK
        # -------------------------
        readiness = evaluate_readiness(plan)

        if readiness.outcome == ReadinessOutcome.NEEDS_INPUT:
            log_event(
                "workflow.needs_input",
                trace_id=approval.trace_id,
                missing=readiness.missing_fields,
            )

            return {
                "status": "awaiting_user_input",
                "missing_fields": readiness.missing_fields,
                "reason": readiness.reason,
            }

        # Resume exactly where we paused
        records = await self._plan_executor.execute(
            trace_id=approval.trace_id,
            steps=plan.steps,
            policy=build_policy_for_workflow("incident_broadcast"),
        )

        # -------------------------
        # 3) SUMMARIZE (LLM -> IncidentSummary JSON)
        # -------------------------
        result = await self._summarizer.summarize(
            trace_id=approval.trace_id,
            records=records,
            safe_user_request=approval.safe_user_request,
            plan=plan,
            user_id=approval.requested_by,
        )

        return result






# ------------------------------
# Helper functions
# ------------------------------



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

async def _gather_preserve_order(coros: list[Any]) -> list[Any]:
    """Gather coroutines concurrently while preserving input order."""
    # asyncio.gather preserves order by default, but keep a wrapper for clarity.
    import asyncio

    return await asyncio.gather(*coros)

def extract_json(text: str) -> dict:
    """
    Extract JSON object from LLM output that may be wrapped in Markdown fences.
    """
    # Remove ```json or ``` and trailing ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)

def parse_llm_json(text: str) -> dict:
    try:
        return extract_json(text)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            f"Failed to parse JSON from LLM output:\n{text}"
        ) from e

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
