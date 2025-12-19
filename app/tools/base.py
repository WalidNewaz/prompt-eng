"""Tool abstraction.

In production, tools might be:
- internal HTTP services (microservices)
- RPC endpoints
- SDK calls (Slack, email provider)
- database actions
- queue producers (Kafka/SQS)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas import ToolName


class ToolExecutor(ABC):
    """Executes a tool by name with validated arguments."""

    @abstractmethod
    async def execute(self, tool_name: ToolName, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return a JSON-serializable result payload."""
        raise NotImplementedError
