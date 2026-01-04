from typing import Protocol

from src.runtime.workflows import IncidentPlan

class PlanGenerator(Protocol):
    async def generate(
        self,
        *,
        trace_id: str,
        workflow: str,
        user_request: str,
        version: str,
        user_id: str | None,
    ) -> IncidentPlan:
        ...
