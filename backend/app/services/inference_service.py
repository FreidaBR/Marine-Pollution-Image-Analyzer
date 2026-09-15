"""Inference provider abstraction.

The backend never calls `ai_service` directly from route code — it goes
through `get_inference_provider()`, which returns one of:

- MockInferenceProvider: deterministic fake detections. Lets backend +
  frontend development proceed today without the trained model.
- RealInferenceProvider: a thin adapter around `ai_service.inference`.

Contract `ai_service` needs to satisfy (see docs/api-contract.md):

    def run_inference(
        image_path: str, model_path: str, confidence_threshold: float
    ) -> list[dict]:
        '''Each dict: {"class_name": str, "confidence": float,
        "bbox": [x_min, y_min, x_max, y_max], "area_ratio": float}.
        Maps directly onto Ultralytics YOLO `Results.boxes` output
        (xyxy + conf + cls -> class_name via ai_service.labels); area_ratio
        is the detection's box area divided by the full image area.
        '''

Optional: `ai_service.labels.LABELS: list[str]` — the shared class-name
enum/list (see app/core/pollution_classes.py), used by the mock provider too
so mock output matches the real model's vocabulary once it exists.

This is an in-process Python import today (no network hop). If `ai_service`
ever becomes its own deployed service, only RealInferenceProvider needs to
change (e.g. to an HTTP call) — routes, schemas, and the DB layer stay the same.
"""

from __future__ import annotations

import hashlib
import random
from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.pollution_classes import get_class_names
from app.schemas.analysis import DetectionOut


class InferenceProvider(Protocol):
    def predict(self, image_path: str, confidence_threshold: float) -> list[DetectionOut]: ...


class MockInferenceProvider:
    """Deterministic fake detections, seeded by the image path so the same
    file always returns the same mock result (useful for tests/demos).
    """

    def __init__(self, class_names: list[str] | None = None) -> None:
        self._class_names = class_names or get_class_names()

    def predict(self, image_path: str, confidence_threshold: float) -> list[DetectionOut]:
        seed = int(hashlib.sha256(image_path.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        num_detections = rng.randint(1, 3)
        detections: list[DetectionOut] = []
        for _ in range(num_detections):
            confidence = round(rng.uniform(confidence_threshold, 1.0), 2)
            x1, y1 = rng.uniform(0, 400), rng.uniform(0, 300)
            x2, y2 = x1 + rng.uniform(20, 150), y1 + rng.uniform(20, 150)
            detections.append(
                DetectionOut(
                    class_name=rng.choice(self._class_names),
                    confidence=confidence,
                    bbox=[x1, y1, x2, y2],
                    area_ratio=round(rng.uniform(0.01, 0.3), 3),
                )
            )
        return detections


class RealInferenceProvider:
    """Adapter around the teammate-owned ai_service.inference module.

    Import is deferred to call time (not module load time) so the backend
    can start up in mock mode even if ai_service's real dependencies
    (ultralytics, opencv, ...) aren't installed yet.
    """

    def __init__(self, model_path: str) -> None:
        if not model_path:
            raise ValueError("MODEL_PATH must be set when AI_MODE=real (see .env.example).")
        self._model_path = model_path

    def predict(self, image_path: str, confidence_threshold: float) -> list[DetectionOut]:
        from ai_service.inference import run_inference  # deferred import

        raw_detections = run_inference(
            image_path=image_path,
            model_path=self._model_path,
            confidence_threshold=confidence_threshold,
        )
        return [
            DetectionOut(
                class_name=d["class_name"],
                confidence=d["confidence"],
                bbox=d["bbox"],
                area_ratio=d.get("area_ratio", 0.0),
            )
            for d in raw_detections
        ]


def get_inference_provider(settings: Settings | None = None) -> InferenceProvider:
    settings = settings or get_settings()

    if settings.ai_mode == "real":
        return RealInferenceProvider(model_path=settings.model_path)

    return MockInferenceProvider(class_names=get_class_names())
