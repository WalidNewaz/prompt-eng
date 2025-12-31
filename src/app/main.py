"""FastAPI "internal tools" service.

This stands in for a company's internal services:
- notifications service (email, Slack)
- ticketing service
- CRM actions
- workflow side effects

Important:
- The service validates inputs (Pydantic)
- Returns structured, schema-stable outputs
- Can be protected with auth, mTLS, or an API gateway in real deployments
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field

from src.api.routes import register_routes

tags_metadata = [
    {
        "name": "Tools",
        "description": "Mocks for internal tools that the AI workflow may invoke"
    },
    {
        "name": "Approvals",
        "description": "Routes that allow manual approvals, of workflows"
    },
    {
        "name": "Demo",
        "description": "All routes to demo the AI services."
    }
]

app = FastAPI(
    title='Prompt Engineering Test Harness',
    version='1.0.0',
    description='Test Harness',
    openapi_tags=tags_metadata
)

# Register all API routes
register_routes(app)

