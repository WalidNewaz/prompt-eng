from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/")
def get_all_agents():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{agent_id}")
def get_agent_by_id(agent_id: int):
    raise HTTPException(status_code=501, detail="Not implemented")