from fastapi import FastAPI

from src.approval.router import router as approvals_router
from .tools import router as tools_router
from .demo import router as demo_router

def register_routes(app: FastAPI):
    app.include_router(approvals_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")
    app.include_router(demo_router, prefix="/v1")