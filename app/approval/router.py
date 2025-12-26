from fastapi import APIRouter, HTTPException
from fastapi import Depends
from sqlalchemy.orm import Session

from app.server.core.container import get_container
from app.db.connection import get_db
from app.approval.repository import ApprovalRequestRepository
from app.approval.models import ApprovalStatus

router = APIRouter(prefix="/approvals", tags=["Approvals"])

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)

@router.get("")
async def get_approvals(
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
):
    """List all approvals."""
    return approval_repository.get_all()

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

