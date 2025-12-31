# ============================================================
# Business/domain entities
# ============================================================
from dataclasses import dataclass
from typing import Any
from datetime import datetime


@dataclass
class ApprovalRequestEntity:
    id: str = None
    trace_id: str = None
    workflow: str = None
    tool_name: str = None
    safe_user_request: str = None
    plan: dict[str, Any] = None
    reason: str = None
    status: str = None
    requested_at: datetime | None = None
    requested_by: str = None
    decided_at: datetime | None = None
    decided_by: str = None
