"""Application settings, loaded from environment variables / .env.

See the repo root `.env.example` for the full list of variables this project
uses. Keeping all of them centralized here (instead of reading os.environ in
random places) is what makes it easy to swap SQLite -> Postgres, or
mock -> real inference, by changing config rather than code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite:///./marine_pollution.db"
    cors_origins: str = "http://localhost:5173"

    # AI
    ai_confidence_threshold: float = 0.40
    ai_mode: str = "real"  # "mock" or "real"
    model_path: str = str(
        Path(__file__).resolve().parents[3]
        / "ai_service"
        / "model"
        / "plastic_trash_detector.pt"
    )

    # Uploads
    max_upload_size_mb: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached Settings instance — env vars are read once per process."""
    return Settings()
