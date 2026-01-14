from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/runs", tags=["Workflow Runs"])

@router.post(
    "",
    summary="Run a workflow",
    description="Runs a workflow and returns the result",
    # response_model=PaginatedResponse[ApprovalRequest],
)
def run_workflow():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{run_id}")
def get_by_id(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{run_id}/steps")
def get_steps(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{run_id}/artifacts")
def get_artifacts(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

# -----------------------------------------
# Observability
# -----------------------------------------

@router.get("/{run_id}/events")
def get_events(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{run_id}/logs")
def get_logs(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{run_id}/traces")
def get_traces(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")



