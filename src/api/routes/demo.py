from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.core.container import get_container
from src.infrastructure.db.connection import get_db
from src.domain.approval.repository import ApprovalRequestRepository


router = APIRouter(prefix="/demo", tags=["Demo"])

class LiveDemoRequest(BaseModel):
    user_request: str
    user_id: str = "demo_user_001"

def get_approval_repo(
    db: Session = Depends(get_db),
) -> ApprovalRequestRepository:
    return ApprovalRequestRepository(db)

@router.post("/")
async def run_live_demo(
    payload: LiveDemoRequest,
    approval_repository: ApprovalRequestRepository = Depends(get_approval_repo),
    container=Depends(get_container),
):
    orchestrator = container.orchestrator
    return await orchestrator.run_incident_broadcast(
        user_request=payload.user_request,
        user_id=payload.user_id,
        approval_repository=approval_repository,
    )