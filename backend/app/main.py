"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --host $BACKEND_HOST --port $BACKEND_PORT
"""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

# When run the documented way (`cd backend && uvicorn app.main:app`), only
# backend/ is on sys.path — the repo root (parent of ai_service/ and
# reporting/) isn't, so the deferred `import ai_service...` / `import
# reporting...` calls in inference_service.py/severity_service.py/
# report_service.py fail with ModuleNotFoundError even when those modules
# are implemented. Pytest doesn't hit this (pyproject.toml's `pythonpath`
# adds the repo root for tests only) — add it here too so it's true for any
# way this app gets started.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api.router import api_router  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.base import create_all  # noqa: E402
from app.services.storage_service import UPLOAD_DIR  # noqa: E402

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


@app.middleware("http")
async def enforce_request_body_limit(request: Request, call_next):
    """Reject oversized requests before FastAPI parses multipart form data."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            request_size = int(content_length)
        except ValueError:
            request_size = 0
        max_request_size = settings.max_upload_size_mb * 1024 * 1024
        if request_size > max_request_size:
            message = f"Request exceeds the {settings.max_upload_size_mb}MB upload limit."
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "file_too_large",
                        "message": message,
                    }
                },
            )
    return await call_next(request)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Marine Pollution Analyzer API is running",
        "docs": "/docs",
        "health": "/health",
        "analyze": "/api/v1/analyze",
    }


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
