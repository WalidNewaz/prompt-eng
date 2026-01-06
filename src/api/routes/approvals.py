from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.api.container import get_container
from src.infrastructure.db.connection import get_db
from src.domain.approval.repository import ApprovalRequestRepository
from src.domain.approval.models import ApprovalStatus
from src.domain.approval.entities import (
    ApprovalRequestEntity as ApprovalRequest,
    Pagination,
    Sorting
)
from src.api.schemas import ApprovalFilters, PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/approvals", tags=["Approvals"])

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)



@router.get(
    "",
    summary="List approval requests",
    description="Returns approval requests filtered by status, users, workflow, and pagination.",
    response_model=PaginatedResponse[ApprovalRequest],
)
async def get_approvals(
    q: ApprovalFilters = Depends(),
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
):
    """
    List approval requests with optional filters.

    Query Parameters:
    - status: Filter by approval status
    - requested_by: Filter by requestor
    - decided_by: Filter by approver/rejector
    - workflow: Filter by workflow name or ID
    - limit: Page size (default: 50)
    - offset: Pagination offset (default: 0)
    """
    filters = ApprovalFilters(
        status=q.status.value if q.status else None,
        requested_by=q.requested_by,
        decided_by=q.decided_by,
        workflow=q.workflow,
    )
    paging = Pagination(limit=q.limit, offset=q.offset)
    sorting = Sorting(sort_by=q.sort_by.value, sort_order=q.sort_order.value)

    page = approval_repository.get_all(
        filters=filters,
        paging=paging,
        sorting=sorting
    )

    return PaginatedResponse(
        data=page.data,
        meta=PaginationMeta(
            total=page.meta.total,
            limit=page.meta.limit,
            offset=page.meta.offset,
            has_next=page.meta.has_next,
            has_previous=page.meta.has_previous,
        ),
    )

@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
):
    """Get a specific approval."""
    result = approval_repository.get(approval_id)
    if not result:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result


@router.post("/{approval_id}/approve")
async def approve_workflow(
    approval_id: str,
    approved_by: str,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
    container=Depends(get_container),
):
    try:
        orchestrator = container.orchestrator
        result = await orchestrator.resume_approved_workflow(
            approval_id=approval_id,
            approved_by=approved_by,
            approval_repository=approval_repository,
        )
        return {
            "status": "EXECUTED",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{approval_id}/reject")
async def reject_workflow(
    approval_id: str,
    approved_by: str,
    reason: str,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
):
    try:
        existing_approval = approval_repository.get(approval_id)
        if not existing_approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        status = existing_approval.status

        if status != ApprovalStatus.PENDING.value:
            raise HTTPException(status_code=400, detail="Cannot reject workflow")

        result = approval_repository.mark_rejected(
            approval_id=approval_id,
            approved_by=approved_by,
            reason=reason,
        )
        return {
            "status": "EXECUTED",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

