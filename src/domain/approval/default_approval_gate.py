from typing import Any

from src.runtime.workflows import IncidentPlan
from src.domain.approval.repository import ApprovalRequestRepositoryProtocol
from src.domain.policies import evaluate_plan, PolicyOutcome
from src.core.errors import OrchestrationError

from .entities import ApprovalGateResult

class DefaultApprovalGate:
    """
    Default approval gate using ApprovalRequestRepository.
    """

    def __init__(self, approval_repository: ApprovalRequestRepositoryProtocol) -> None:
        self._repo = approval_repository

    def evaluate(
        self,
        *,
        trace_id: str,
        workflow: str,
        safe_user_request: str,
        plan: IncidentPlan,
        policy: Any,
        user_id: str | None,
    ) -> ApprovalGateResult:
        decisions = evaluate_plan(policy, [s.name for s in plan.steps])

        for d in decisions:
            if d.outcome == PolicyOutcome.DENY:
                raise OrchestrationError(d.reason)

        approval_needed = [
            d for d in decisions
            if d.outcome == PolicyOutcome.REQUIRE_APPROVAL
        ]

        if not approval_needed:
            return ApprovalGateResult(proceed=True)

        approval_id = self._repo.create_pending(
            trace_id=trace_id,
            workflow=workflow,
            tool_name=", ".join(d.tool.value for d in approval_needed),
            safe_user_request=safe_user_request,
            plan=plan.model_dump(),
            reason="One or more tools require approval.",
            requested_by=user_id,
        )

        return ApprovalGateResult(
            proceed=False,
            response={
                "status": "approval_required",
                "approval_id": approval_id,
                "tools": [d.tool.value for d in approval_needed],
            },
        )
