"""Test configuration.

Sets environment variables *before* anything under `app` is imported, so
`Settings` (cached via lru_cache) and the SQLAlchemy engine pick up an
isolated, disposable test database and mock inference mode.
"""

import os
import pathlib

_TEST_DB_PATH = pathlib.Path(__file__).parent / "test_marine_pollution.db"

os.environ.setdefault("AI_MODE", "mock")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    _TEST_DB_PATH.unlink(missing_ok=True)

    import shutil

    from app.services.storage_service import UPLOAD_DIR

    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
