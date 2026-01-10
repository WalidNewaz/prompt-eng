from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.container import get_container
from src.domain.approval import ApprovalGate, DefaultApprovalGate
from src.infrastructure.db.connection import get_db
from src.domain.approval.repository import ApprovalRequestRepository

router = APIRouter(prefix="/workflows", tags=["Workflows"])

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)

def get_approval_gate(db: Session = Depends(get_db)) -> ApprovalGate:
    approval_repository = ApprovalRequestRepository(db)
    # approval_repo = Depends(get_approval_repo)
    return DefaultApprovalGate(approval_repository)


class IncidentBroadcastRequest(BaseModel):
    user_request: str
    user_id: str = "demo_user_001"

@router.post(
    "/incident_broadcast",
    summary="Report incident",
    description="Execute the Incident Broadcast workflow."
)
async def handle_incident_broadcast(
    payload: IncidentBroadcastRequest,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
    approval_gate: ApprovalGate = Depends(get_approval_gate),
    container=Depends(get_container),
):
    orchestrator = container.orchestrator
    return await orchestrator.run_incident_broadcast(
        user_request=payload.user_request,
        user_id=payload.user_id,
        # approval_repository=approval_repository,
        approval_gate=approval_gate,
    )