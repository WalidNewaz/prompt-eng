from typing import Protocol, Any

from src.runtime.workflows import IncidentPlan
from .entities import ApprovalGateResult

class ApprovalGate(Protocol):
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
        ...
