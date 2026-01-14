from fastapi import APIRouter, HTTPException, Depends


router = APIRouter(prefix="/models", tags=["Models"])

@router.get("", summary="List all models")
async def list_models():
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{model_id}", summary="Get model information")
async def get_model(model_id: int):
    raise HTTPException(status_code=501, detail="Not implemented")