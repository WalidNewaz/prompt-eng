from fastapi import FastAPI

from .approvals import router as approvals_router
from .tools import router as tools_router
from .demo import router as demo_router
from .workflows import router as workflows_router
from .runs import router as runs_router
from .cases import router as cases_router
from .artifacts import router as artifacts_router
from .models import router as models_router
from .steps import router as steps_router
from .agents import router as agents_router

def register_routes(app: FastAPI):
    app.include_router(demo_router, prefix="/v1")
    app.include_router(models_router, prefix="/v1")
    app.include_router(agents_router, prefix="/v1")
    app.include_router(workflows_router, prefix="/v1")
    app.include_router(cases_router, prefix="/v1")
    app.include_router(artifacts_router, prefix="/v1")
    app.include_router(approvals_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")
    app.include_router(steps_router, prefix="/v1")