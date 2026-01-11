from typing import Optional, Generic, List, TypeVar, Annotated, Any
import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, BeforeValidator

from src.domain.approval.models import ApprovalStatus

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class ApprovalSortField(str, Enum):
    requested_at = "requested_at"
    status = "status"
    workflow = "workflow"

class ApprovalFilters(BaseModel):
    """
    Query filters for listing approval requests.

    All fields are optional.
    Defaults are chosen to be safe for production usage.
    """

    # Filtering
    status: Optional[ApprovalStatus] = Field(
        default=ApprovalStatus.PENDING,
        description="Filter approvals by status"
    )

    requested_by: Optional[str] = Field(
        default=None,
        description="User who requested the approval"
    )

    decided_by: Optional[str] = Field(
        default=None,
        description="User who approved or rejected the request"
    )

    workflow: Optional[str] = Field(
        default=None,
        description="Workflow identifier or name"
    )

    # Pagination
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of records to return (1–100)"
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip (pagination)"
    )

    # Sorting
    sort_by: ApprovalSortField = Field(
        default=ApprovalSortField.requested_at,
        description="Field to sort by"
    )
    sort_order: SortOrder = Field(
        default=SortOrder.desc,
        description="Sort order (asc or desc)"
    )

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta

