"""
API v1 router
"""
from fastapi import APIRouter
from app.api.v1 import health, jobs, ai, settings

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(settings.router, tags=["settings"])

