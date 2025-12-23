from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.runtime.workflows import PlannedToolCall
from app.schemas import ToolName


def test_planned_tool_call_accepts_parallel_group() -> None:
    step = PlannedToolCall(
        name=ToolName.SEND_EMAIL,
        arguments={"to": "dev@example.com", "subject": "S", "body": "B"},
        parallel_group="broadcast_1",
    )
    assert step.parallel_group == "broadcast_1"
