from fastapi import APIRouter, Depends, HTTPException
from fastapi import Depends
from sqlalchemy.orm import Session

from app.server.core.container import get_container
from app.db.connection import get_db
from app.approval.repository import ApprovalRequestRepository

router = APIRouter(prefix="/approvals", tags=["Approvals"])

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)

@router.post("/{approval_id}/approve")
async def approve_workflow(
    approval_id: str,
    approved_by: str,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
    container=Depends(get_container),
):
    try:
        orchestrator = container
        result = await orchestrator.resume_approved_workflow(
            approval_id=approval_id,
            approved_by=approved_by,
        )
        return {
            "status": "EXECUTED",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
