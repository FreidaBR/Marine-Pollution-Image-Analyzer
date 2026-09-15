"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --host $BACKEND_HOST --port $BACKEND_PORT
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import create_all
from app.services.storage_service import UPLOAD_DIR

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Dev-friendly table creation. Once the schema stabilizes and this runs
    # against a shared/persistent database, replace with an Alembic migration.
    create_all()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Marine Pollution Image Analyzer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serves uploaded images back out at e.g. /uploads/ANL-0001.jpg, matching
# the `image_url` field in the frozen API contract (docs/api-contract.md).
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# Per docs/api-contract.md: "Errors must use: {"error": {"code", "message"}}".
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        error_body = detail
    else:
        error_body = {"code": "http_error", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error_body})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": exc.errors(),
            }
        },
    )
