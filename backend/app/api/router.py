from fastapi import APIRouter

from app.api.routes import analyze, health, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(reports.router)
