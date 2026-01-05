from typing import Protocol, Any

from src.runtime.workflows import (
    ExecutionRecord,
    IncidentPlan,
)

class WorkflowSummarizer(Protocol):
    async def summarize(
        self,
        *,
        trace_id: str,
        records: list[ExecutionRecord],
        safe_user_request: str,
        plan: IncidentPlan,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Produce a structured summary of a workflow execution.

        Raises:
            OrchestrationError on invalid or unsafe output.
        """
        ...
