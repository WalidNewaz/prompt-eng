from unittest.mock import MagicMock, AsyncMock

from src.runtime.workflows import (
    ExecutionRecord,
)
from src.schemas import (
    ToolName,
)

mock_plan_executor = MagicMock()
mock_plan_executor.execute = AsyncMock(
    return_value=[
        ExecutionRecord(
            name=ToolName.SEND_SLACK_MESSAGE,
            ok=True,
            result={"ok": True},
            parallel_group=None,
        )
    ]
)

