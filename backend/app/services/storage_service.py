"""Saves uploaded images to disk under uploads/ (already gitignored at the
repo root, and served back out at /uploads via StaticFiles in main.py).
Kept as its own module so swapping to e.g. S3 later only means changing
this one file.
"""

from __future__ import annotations

import pathlib

from fastapi import UploadFile

UPLOAD_DIR = pathlib.Path(__file__).resolve().parents[3] / "uploads"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class UploadValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def validate_upload(file: UploadFile, max_size_mb: int) -> bytes:
    """Read a bounded upload and return its validated raw bytes."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            "invalid_file_type",
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}.",
        )

    max_bytes = max_size_mb * 1024 * 1024
    declared_size = file.size
    if declared_size is not None and declared_size > max_bytes:
        raise UploadValidationError(
            "file_too_large",
            f"File exceeds the {max_size_mb}MB upload limit.",
            status_code=413,
        )

    chunks: list[bytes] = []
    total_size = 0
    chunk_size = 1024 * 1024
    while chunk := file.file.read(chunk_size):
        total_size += len(chunk)
        if total_size > max_bytes:
            raise UploadValidationError(
                "file_too_large",
                f"File exceeds the {max_size_mb}MB upload limit.",
                status_code=413,
            )
        chunks.append(chunk)

    contents = b"".join(chunks)
    if len(contents) == 0:
        raise UploadValidationError("empty_file", "Uploaded file is empty.")

    return contents


def save_bytes(contents: bytes, stem: str, original_filename: str) -> str:
    """Writes `contents` to uploads/<stem><ext-from-original-filename>.

    Returns the stored file's public path relative to /uploads (e.g.
    "ANL-0001.jpg"), used to build `image_url`.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    suffix = pathlib.Path(original_filename or "").suffix or ".jpg"
    stored_name = f"{stem}{suffix}"
    (UPLOAD_DIR / stored_name).write_bytes(contents)
    return stored_name
