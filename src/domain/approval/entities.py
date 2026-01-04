# ============================================================
# Business/domain entities
# ============================================================
from dataclasses import dataclass
from typing import Any, Optional, Literal
from datetime import datetime

SortOrderLiteral = Literal["asc", "desc"]
ApprovalSortFieldLiteral = Literal["requested_at", "status", "workflow"]
ApprovalStatusLiteral = Literal["PENDING", "APPROVED", "REJECTED"]

@dataclass(frozen=True)
class ApprovalGateResult:
    proceed: bool
    response: dict[str, Any] | None = None


@dataclass(frozen=True)
class ApprovalFilters:
    status: Optional[ApprovalStatusLiteral] = None
    requested_by: Optional[str] = None
    decided_by: Optional[str] = None
    workflow: Optional[str] = None


@dataclass(frozen=True)
class Pagination:
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class Sorting:
    sort_by: ApprovalSortFieldLiteral = "requested_at"
    sort_order: SortOrderLiteral = "desc"


@dataclass(frozen=True)
class PageMeta:
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool


@dataclass(frozen=True)
class PageResult:
    data: list["ApprovalRequest"]
    meta: PageMeta

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
