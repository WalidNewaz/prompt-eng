from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/steps", tags=["Steps"])

# -----------------------------------------
# Step
# -----------------------------------------

@router.get("/{step_id}")
def get_step(run_id: str, step_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

# -----------------------------------------
# Execution Control
# -----------------------------------------

@router.post("/{step_id}/cancel")
def cancel_by_id(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/{step_id}/pause")
def pause_by_id(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/{step_id}/resume")
def resume_by_id(run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/{step_id}/retry")
def retry_by_id(run_id: str, step_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

# -----------------------------------------
# Human in the Loop
# -----------------------------------------

@router.post("/{step_id}/approve")
def approve_by_id(run_id: str, step_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{step_id}/required_inputs")
def required_inputs(run_id: str, step_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/{step_id}/inputs")
def inputs(run_id: str, step_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")