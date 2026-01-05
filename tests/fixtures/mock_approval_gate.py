from unittest.mock import MagicMock

from src.runtime.workflows import IncidentPlan
from src.security.policy import SecurityPolicy
from src.domain.approval.entities import ApprovalGateResult

def conditional_evaluate(
    *,
    trace_id: str,
    workflow: str,
    plan: IncidentPlan,
    policy: SecurityPolicy,
    user_id: str | None,
):
    if policy.approval_required_tools:
        return ApprovalGateResult(
            proceed=False,
            response={
                "status": "approval_required",
                "approval_id": "approval_123",
                "tools": [tool.value for tool in policy.approval_required_tools],
            }
        )
    return ApprovalGateResult(proceed=True)

mock_approval_gate = MagicMock()
# mock_approval_gate.evaluate.return_value = ApprovalGateResult(proceed=True)
mock_approval_gate.evaluate.side_effect = conditional_evaluate