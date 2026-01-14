from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/artifacts", tags=["Artifacts"])

@router.get(
    "/{artifact_id}",
    summary="Get artifact metadata",
)
def get_artifact(artifact_id: str):
    raise HTTPException(status_code=501, detail="Not implemented")