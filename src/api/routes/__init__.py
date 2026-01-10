from fastapi import FastAPI

from .approvals import router as approvals_router
from .tools import router as tools_router
from .demo import router as demo_router
from .workflows import router as workflows_router

def register_routes(app: FastAPI):
    app.include_router(approvals_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")
    app.include_router(demo_router, prefix="/v1")
    app.include_router(workflows_router, prefix="/v1")