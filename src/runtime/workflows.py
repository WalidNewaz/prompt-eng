"""Workflow models and DAG execution.

We represent a plan as:
- steps: list of executable tool calls
- groups: steps can share a `parallel_group` to run concurrently
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.tools.schemas import ToolCall, ToolName


class PlannedToolCall(BaseModel):
    """A planned tool call emitted by the planner model."""
    name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    parallel_group: str | None = None


class ExecutionRecord(BaseModel):
    """Execution result for a tool call."""
    name: ToolName
    ok: bool
    result: dict[str, Any]
    parallel_group: str | None = None


class IncidentPlan(BaseModel):
    """Planner output for the incident broadcast workflow."""
    intent: Literal['incident_broadcast'] = 'incident_broadcast'
    steps: list[PlannedToolCall]


class IncidentSummary(BaseModel):
    """Summarizer output (structured) after executing the plan."""
    incident_title: str
    actions_taken: list[str]
    tool_outcomes: list[str]
    next_steps: list[str]


def to_toolcall_dict(step: PlannedToolCall) -> dict[str, Any]:
    """Convert a planned step to the ToolCall envelope dict expected by the harness."""
    tc = ToolCall(name=step.name, arguments=step.arguments)
    return tc.model_dump()
