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

from app.llm.base import LLMClient, LLMRequest
from app.observability.tracing import Span, log_event, new_trace_id
from app.prompts.loader import load_prompt
from app.runtime.harness import PromptToolHarness, ToolExecutionError
from app.runtime.renderer import PromptRenderer
from app.runtime.workflows import (
    ExecutionRecord,
    IncidentPlan,
    IncidentSummary,
    PlannedToolCall,
    to_toolcall_dict,
)
from app.schemas import (
    ToolName,
    validate_tool_call_payload
)
from app.security.policy import (
    assert_all_tools_allowed,
    build_policy_for_workflow,
    sanitize_message,
    sanitize_user_text,
    evaluate_plan,
    PolicyViolation,
)
from app.security.policy_decision import PolicyOutcome
from app.runtime.repair import build_repair_prompt
from app.runtime.approval import plan_requires_approval
from app.approval.repository import ApprovalRequestRepositoryProtocol
from app.approval.models import ApprovalStatus

BASE_DIR = Path(__file__).resolve().parents[1]


class LLMParseError(Exception):
    pass

class OrchestrationError(RuntimeError):
    """Raised when orchestration fails after retries."""
    pass


class Orchestrator:
    """Coordinates prompt execution, validation, and repair."""

    def __init__(
        self,
        *,
        llm: LLMClient,
        harness: PromptToolHarness,
        # approval_repository: ApprovalRequestRepositoryProtocol,
        renderer: PromptRenderer | None = None,
        max_retries: int = 1,
    ) -> None:
        self._llm = llm
        self._harness = harness
        # self._approval_repository = approval_repository
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
        plan_schema = _load_json_schema(f'{BASE_DIR}/prompts/incident_plan/{tool_plan_version}/schema.json')

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
            log_event(
                'span.end',
                trace_id=trace_id,
                span=plan_span,
                usage=getattr(llm_plan_resp, 'usage', None).__dict__ if 'llm_plan_resp' in locals() else None,
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
            # assert_all_tools_allowed(policy, [s.name for s in plan.steps], workflow='incident_broadcast')
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
        # APPROVAL GATE
        # -------------------------
        if plan_requires_approval(plan):
            approval_id = approval_repository.create_pending(
                trace_id=trace_id,
                workflow="incident_broadcast",
                safe_user_request=safe_user_request,
                plan=plan.model_dump(),
                requested_by=user_id,
            )

            log_event(
                "workflow.awaiting_approval",
                trace_id=trace_id,
                approval_id=approval_id,
                steps=len(plan.steps),
            )

            return {
                "trace_id": trace_id,
                "status": ApprovalStatus.PENDING.value,
                "approval_id": approval_id,
                "plan": plan.model_dump(),
            }

        # -------------------------
        # 2) EXECUTE (DAG: parallel groups + join)
        # -------------------------
        exec_span = Span(name='tools.execute_dag', trace_id=trace_id)
        exec_span.attributes['step_count'] = len(plan.steps)

        try:
            records = await self._execute_plan_dag(trace_id=trace_id, steps=plan.steps, policy=policy)
        finally:
            exec_span.end()
            log_event('span.end', trace_id=trace_id, span=exec_span)

        # -------------------------
        # 3) SUMMARIZE (LLM -> IncidentSummary JSON)
        # -------------------------
        return await self._summarize_execution(
            trace_id=trace_id,
            records=records,
            safe_user_request=safe_user_request,
            plan=plan,
            user_id=user_id,
        )


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

        # Resume exactly where we paused
        records = await self._execute_plan_dag(
            trace_id=approval.trace_id,
            steps=plan.steps,
            policy=build_policy_for_workflow("incident_broadcast"),
        )

        # Continue to summary phase (reuse existing logic)
        return await self._summarize_execution(
            trace_id=approval.trace_id,
            records=records,
            safe_user_request=approval.safe_user_request,
            plan=plan,
            user_id=approval.requested_by,
        )

    async def _execute_plan_dag(
            self,
            *,
            trace_id: str,
            steps: list[PlannedToolCall],
            policy: Any,
    ) -> list[ExecutionRecord]:
        """Execute planned steps with parallel groups."""
        # Group steps by parallel_group; None group runs sequentially
        sequential: list[PlannedToolCall] = [s for s in steps if not s.parallel_group]
        grouped: dict[str, list[PlannedToolCall]] = {}
        for s in steps:
            if s.parallel_group:
                grouped.setdefault(s.parallel_group, []).append(s)

        records: list[ExecutionRecord] = []

        # First run all parallel groups (each group in parallel within itself; groups sequential)
        for group_id, group_steps in grouped.items():
            log_event('dag.group.start', trace_id=trace_id, group=group_id, size=len(group_steps))

            async def _run_one(step: PlannedToolCall) -> ExecutionRecord:
                policy.assert_tool_allowed(step.name)
                # Minimal sanitization for outgoing content
                args = dict(step.arguments)
                if step.name == ToolName.SEND_SLACK_MESSAGE and 'text' in args:
                    args['text'] = sanitize_message(str(args['text']))
                if step.name == ToolName.SEND_EMAIL:
                    if 'subject' in args:
                        args['subject'] = sanitize_message(str(args['subject']))
                    if 'body' in args:
                        args['body'] = sanitize_message(str(args['body']))

                tool_call_dict = {'name': step.name.value, 'arguments': args}
                tool_span = Span(name=f'tool.{step.name.value}', trace_id=trace_id)
                try:
                    result = await self._harness.run_tool_call(tool_call_dict)
                    ok = bool(result.get('ok', False))
                    return ExecutionRecord(
                        name=step.name,
                        ok=ok,
                        result=result,
                        parallel_group=step.parallel_group,
                    )
                except ToolExecutionError as exc:
                    return ExecutionRecord(
                        name=step.name,
                        ok=False,
                        result={'ok': False, 'error': str(exc)},
                        parallel_group=step.parallel_group,
                    )
                finally:
                    tool_span.end()
                    log_event('span.end', trace_id=trace_id, span=tool_span)

            group_records = await _gather_preserve_order([_run_one(s) for s in group_steps])
            records.extend(group_records)
            log_event('dag.group.end', trace_id=trace_id, group=group_id, ok=all(r.ok for r in group_records))

        # Then run sequential steps
        for step in sequential:
            log_event('dag.step.start', trace_id=trace_id, tool=step.name.value)
            policy.assert_tool_allowed(step.name)

            tool_call_dict = to_toolcall_dict(step)
            tool_span = Span(name=f'tool.{step.name.value}', trace_id=trace_id)
            try:
                result = await self._harness.run_tool_call(tool_call_dict)
                ok = bool(result.get('ok', False))
                records.append(
                    ExecutionRecord(name=step.name, ok=ok, result=result, parallel_group=None)
                )
            except ToolExecutionError as exc:
                records.append(
                    ExecutionRecord(
                        name=step.name,
                        ok=False,
                        result={'ok': False, 'error': str(exc)},
                        parallel_group=None,
                    )
                )
            finally:
                tool_span.end()
                log_event('span.end', trace_id=trace_id, span=tool_span)

        return records

    async def _summarize_execution(
            self,
            *,
            trace_id: str,
            summary_version: str = 'v1',
            records: list[ExecutionRecord],
            safe_user_request: str,
            plan: IncidentPlan,
            user_id: str | None = None,
    ):
        summary_span = Span(name='llm.summarize', trace_id=trace_id)
        summary_template = load_prompt('incident_summary', summary_version)

        tool_outcomes_json = json.dumps([r.model_dump() for r in records], ensure_ascii=False)
        summary_prompt = self._renderer.render(
            summary_template,
            {'user_request': safe_user_request, 'tool_outcomes_json': tool_outcomes_json},
        )

        try:
            # Structured output schema for summary
            summary_schema = _load_json_schema(f'{BASE_DIR}/prompts/incident_summary/{summary_version}/schema.json')
            llm_summary_resp = await self._llm.generate(
                LLMRequest(
                    prompt=summary_prompt,
                    metadata={
                        'trace_id': trace_id,
                        'module': 'incident_summary',
                        'version': summary_version
                    },
                    safety_identifier=user_id,
                    json_schema=summary_schema,
                )
            )
        finally:
            summary_span.end()
            log_event(
                'span.end',
                trace_id=trace_id,
                span=summary_span,
                usage=getattr(llm_summary_resp, 'usage', None).__dict__ if 'llm_summary_resp' in locals() else None,
            )

        try:
            summary_obj = json.loads(llm_summary_resp.output_text.strip())
            summary = IncidentSummary.model_validate(summary_obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            log_event(
                'workflow.summary.invalid',
                trace_id=trace_id,
                error=str(exc),
                raw_output=llm_summary_resp.output_text,
            )
            raise OrchestrationError(f'Summary produced invalid JSON: {exc}') from exc

        log_event('workflow.end', trace_id=trace_id, ok=True)

        return {
            'trace_id': trace_id,
            'plan': plan.model_dump(),
            'tool_execution_records': [r.model_dump() for r in records],
            'summary': summary.model_dump(),
        }




# ------------------------------
# Helper functions
# ------------------------------

def _load_json_schema(path: str) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding='utf-8'))

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
