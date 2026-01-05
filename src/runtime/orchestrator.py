"""End-to-end orchestration:
    prompt selection -> render prompt -> LLM Plan -> validate -> Approve -> tool execute -> repair.

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

from src.core.errors import LLMParseError, OrchestrationError
from src.core.types import WorkflowDefinition
from src.llm.base import LLMClient, LLMRequest
from src.observability.tracing import Span, log_event, new_trace_id
from src.runtime.harness import PromptToolHarness, ToolExecutionError
from src.runtime.prompt_renderer import PromptRenderer
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
from src.domain.policies.policy_provider import PolicyProvider
from src.domain.policies.default_policy_provider import DefaultPolicyProvider
from src.domain.plans.plan_generator import PlanGenerator
from src.domain.plans.llm_plan_generator import LLMPlanGenerator
from src.domain.prompt.prompt_store import PromptStore
from src.domain.prompt.file_system_prompt_store import FilesystemPromptStore
from src.domain.approval.approval_gate import ApprovalGate
from src.domain.approval.default_approval_gate import DefaultApprovalGate

from .plan_executor import PlanExecutor
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
        workflow: WorkflowDefinition,
        policy_provider: PolicyProvider | None = None,
        prompt_store: PromptStore | None = None,
        plan_generator: PlanGenerator | None = None,
        plan_executor: PlanExecutor | None = None,
        prompt_renderer: PromptRenderer | None = None,
        approval_gate: ApprovalGate | None = None,
        summarizer: WorkflowSummarizer | None = None,
        max_retries: int = 1,
    ) -> None:
        self._llm = llm
        self._harness = harness
        self._workflow = workflow
        self._policy_provider = policy_provider or DefaultPolicyProvider()
        self._prompt_store = prompt_store or FilesystemPromptStore(base_dir=BASE_DIR)
        self._prompt_renderer = prompt_renderer or PromptRenderer()
        self._plan_generator = plan_generator or LLMPlanGenerator(
            llm=self._llm,
            prompt_store=self._prompt_store,
            renderer=self._prompt_renderer,
        )
        self._plan_executor = plan_executor or PlanExecutor(harness=harness)
        self._approval_gate = approval_gate or DefaultApprovalGate()
        self._summarizer = summarizer or LLMWorkflowSummarizer(
            llm=llm,
            renderer=self._prompt_renderer,
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
        trace_id = new_trace_id()
        plan_span = Span(name='llm.plan', trace_id=trace_id)
        safe_user_request = sanitize_user_text(user_request)
        log_event('workflow.start', trace_id=trace_id, workflow='notification')


        meta = metadata or {}
        template = self._prompt_store.get_prompt(
            workflow='notification',
            module="notification",
            version=prompt_version,
        )
        schema = self._prompt_store.get_schema(
            workflow='notification',
            module="notification",
            version=prompt_version,
        )
        prompt = self._prompt_renderer.render(
            template,
            {"user_request": user_request},
        )

        last_error: Exception | None = None
        # current_prompt = rendered

        for attempt in range(self._max_retries + 1):
            llm_resp = await self._llm.generate(
                LLMRequest(
                    prompt=prompt,
                    metadata={
                        **meta,
                        'prompt_module': 'notification',
                        'prompt_version': prompt_version,
                        'attempt': attempt,
                    },
                    json_schema=schema,
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
                    original_prompt=prompt,
                    invalid_output_text=llm_resp.output_text,
                    error_message=str(exc),
                )
            except ToolExecutionError as exc:
                # Tool validation/execution failures are also repairable (wrong args, missing fields).
                last_error = exc
                if attempt >= self._max_retries:
                    break
                current_prompt = build_repair_prompt(
                    original_prompt=prompt,
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
        """
        Execute the Incident Broadcast workflow.

        Pipeline:
            1) Sanitize user input (removes unsafe content for prompting/logging)
            2) Generate a structured IncidentPlan using the LLM (JSON-schema constrained)
            3) Evaluate policy decisions for tools in the plan:
                - DENY -> abort with OrchestrationError
                - REQUIRE_APPROVAL -> persist pending approval and return early
            4) Validate readiness (missing required fields -> return awaiting_user_input)
            5) Execute tool steps via PlanExecutor (supports parallel groups)
            6) Summarize execution via WorkflowSummarizer (JSON-schema constrained)

        Returns:
            A dict with one of the following shapes:

            - Approval required:
                {"status": "approval_required", "approval_id": str, "tools": list[str]}

            - Awaiting input:
                {"status": "awaiting_user_input", "missing_fields": list[str], "reason": str}

            - Completed:
                {"trace_id": str, "plan": {...}, "tool_execution_records": [...], "summary": {...}}

        Raises:
            OrchestrationError:
                - invalid plan JSON
                - policy denied tools
                - approval repository missing when required
                - summarizer output invalid
        """
        trace_id = new_trace_id()
        policy = self._policy_provider.for_workflow(workflow='incident_broadcast', user_id=user_id)

        safe_user_request = sanitize_user_text(user_request)
        log_event('workflow.start', trace_id=trace_id, workflow='incident_broadcast')

        # -------------------------
        # PLAN (LLM -> IncidentPlan JSON)
        # -------------------------
        plan = await self._plan_generator.generate(
            trace_id=trace_id,
            workflow='incident_broadcast',
            user_request=safe_user_request,
            version=tool_plan_version,
            user_id=user_id,
        )

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
        approval = self._approval_gate.evaluate(
            trace_id=trace_id,
            workflow='incident_broadcast',
            plan=plan,
            policy=policy,
            user_id=user_id,
        )

        if not approval.proceed:
            return approval.response

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
        # EXECUTE (DAG: parallel groups + join)
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

        # -------------------------
        # EXECUTE (DAG: parallel groups + join)
        # -------------------------
        exec_span = Span(name='tools.execute_dag', trace_id=approval.trace_id)
        exec_span.attributes['step_count'] = len(plan.steps)

        try:
            records = await self._plan_executor.execute(
                trace_id=approval.trace_id,
                steps=plan.steps,
                policy=build_policy_for_workflow("incident_broadcast"),
            )
        finally:
            exec_span.end()
            log_event('span.end', trace_id=approval.trace_id, span=exec_span)

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







