"""Severity calculation, per docs/api-contract.md and the project brief's
severity table:

    Low       few low-confidence or isolated indicators
    Moderate  several visible indicators or medium confidence
    High      multiple clear indicators, oil-like pattern, or dense waste
    Critical  extensive visible contamination or multiple severe indicators

Prefers the teammate-owned `reporting.severity` implementation once it
exists. Falls back to a documented local heuristic so the analyze pipeline
works end-to-end before that module is implemented.

Contract `reporting.severity` should satisfy, if/when implemented:

    def calculate_severity(detections: list[dict]) -> dict:
        '''detections: [{"class_name": str, "confidence": float,
        "bbox": [...], "area_ratio": float}]
        Returns {"severity": "Low"|"Moderate"|"High"|"Critical",
        "severity_score": int (0-100)}.'''
"""

from __future__ import annotations

from app.core.pollution_classes import NON_POLLUTION_CLASS
from app.schemas.analysis import DetectionOut

_OIL_LIKE_CLASS = "oil_slick"


def _pollution_detections(detections: list[DetectionOut]) -> list[DetectionOut]:
    return [d for d in detections if d.class_name != NON_POLLUTION_CLASS]


def dominant_category(detections: list[DetectionOut]) -> str:
    pollution = _pollution_detections(detections)
    if not pollution:
        return NON_POLLUTION_CLASS
    return max(pollution, key=lambda d: d.confidence).class_name


def _fallback_calculate_severity(detections: list[DetectionOut]) -> dict:
    pollution = _pollution_detections(detections)
    if not pollution:
        return {"severity": "Low", "severity_score": 0}

    max_confidence = max(d.confidence for d in pollution)
    count = len(pollution)
    has_oil_like = any(d.class_name == _OIL_LIKE_CLASS for d in pollution)

    # Transparent, documented scoring: confidence contributes up to 60,
    # detection count contributes up to 30 (capped at 5 detections), an
    # oil-like pattern adds a flat bump reflecting its higher visible risk.
    score = round(max_confidence * 60 + min(count, 5) * 6 + (10 if has_oil_like else 0))
    score = max(0, min(100, score))

    if score >= 75 or count >= 5:
        severity = "Critical"
    elif score >= 50 or has_oil_like:
        severity = "High"
    elif score >= 25:
        severity = "Moderate"
    else:
        severity = "Low"

    return {"severity": severity, "severity_score": score}


def calculate_severity(detections: list[DetectionOut]) -> dict:
    try:
        from reporting.severity import calculate_severity as real_calculate_severity
    except Exception:
        return _fallback_calculate_severity(detections)

    raw = [d.model_dump() for d in detections]
    return real_calculate_severity(raw)
