from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.container import get_container
from src.infrastructure.db.connection import get_db
from src.repository.approval_repository import ApprovalRequestRepository


router = APIRouter(prefix="/demo", tags=["Demo"])

class LiveDemoRequest(BaseModel):
    user_request: str
    user_id: str = "demo_user_001"

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)

@router.get("/run-tool-calls", summary="Run tool calls")
async def run_tool_calls():
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/incident-broadcast-no-approval",
    summary="Report incident / no approval required",
    description="Execute the Incident Broadcast workflow."
)
async def run_live_demo(
    payload: LiveDemoRequest,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
    container=Depends(get_container),
):
    orchestrator = container.orchestrator
    return await orchestrator.run_incident_broadcast(
        user_request=payload.user_request,
        user_id=payload.user_id,
        # approval_repository=approval_repository,
    )

@router.get("/incident-broadcast-approval-required", summary="Report incident / approval required")
async def run_incident_broadcast_approval_required():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/incident-broadcast-approval-required/approve", summary="Approve incident broadcast workflow")
async def approve_incident_broadcast():
    raise HTTPException(status_code=501, detail="Not implemented")