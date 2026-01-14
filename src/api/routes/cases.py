from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("/")
def create_case():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/")
def get_all_cases():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{case_id}")
def get_by_id(case_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{case_id}/workflows")
def get_cases_workflows():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{case_id}/runs")
def get_runs_by_id(case_id: str, run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{case_id}/artifacts")
def get_artifacts(case_id: str, run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{case_id}/history")
def get_history(case_id: str, run_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")
