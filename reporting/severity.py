"""
Standalone Visual Pollution Severity Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Calculates an Image-Based Visual Pollution Indicator Score [0 - 100]
and maps it to qualitative severity tiers: Clean, Low, Moderate, High, Critical.

NOTE: This is an image-based visual indicator score, NOT laboratory-confirmed chemical pollution.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Tuple, Optional, Union
from reporting.schemas import SeverityLevel, Detection


# Configurable scoring weights and boundary thresholds.
# Easy to tune for demo/presentation during hackathon calibration.
SEVERITY_CONFIG: Dict[str, Any] = {
    # Severity level threshold boundaries (inclusive lower bound)
    "thresholds": {
        "critical": 85,
        "high": 60,
        "moderate": 30,
        "low": 1,
        "clean": 0,
    },
    # Maximum points allocated to each sub-component (sum = 100)
    "component_weights": {
        "detection_count": 35.0,     # Impact of debris quantity
        "avg_confidence": 20.0,      # Average model confidence
        "max_confidence": 15.0,      # Highest single indicator confidence
        "coverage_or_density": 30.0, # Visible area ratio or spatial density fallback
    },
    # Parameter saturation targets
    "count_saturation": 12,          # Detection count that achieves full count score
    "coverage_saturation": 0.25,     # Visible area ratio (25% of image) that achieves full coverage score
    # Class importance multipliers (defaults to 1.0 for marine debris)
    "class_weights": {
        "marine_debris": 1.0,
        "plastic_debris": 1.0,
        "floating_waste": 1.0,
        "debris": 1.0,
        "default": 1.0,
    },
}


def normalize_detection(raw: Union[Detection, Dict[str, Any], Tuple[Any, ...], List[Any]]) -> Detection:
    """
    Adapter layer: Normalizes raw YOLO predictions into a standardized Detection object.
    Supports:
      - Detection instance
      - Dict with keys: ('class_name'/'class'/'label', 'confidence'/'conf', 'bbox'/'box', optional 'area_ratio')
      - Tuple or List: (class_name, confidence, bbox) or (class_name, confidence, bbox, area_ratio)
    """
    if isinstance(raw, Detection):
        return raw

    if isinstance(raw, dict):
        bbox = raw.get("bbox") or raw.get("box")
        if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError(f"Detection dictionary must contain a valid 4-element 'bbox' or 'box', got: {raw}")
        class_name = str(raw.get("class_name") or raw.get("class") or raw.get("label") or "marine_debris")
        raw_conf = raw.get("confidence") if "confidence" in raw else raw.get("conf", 0.5)
        confidence = float(raw_conf)
        area_ratio = raw.get("area_ratio")
        if area_ratio is not None:
            area_ratio = float(area_ratio)
        return Detection(
            class_name=class_name,
            confidence=confidence,
            bbox=[float(x) for x in bbox],
            area_ratio=area_ratio,
        )

    if isinstance(raw, (tuple, list)):
        if len(raw) >= 3:
            class_name = str(raw[0])
            confidence = float(raw[1])
            bbox = [float(x) for x in raw[2]]
            area_ratio = float(raw[3]) if len(raw) > 3 and raw[3] is not None else None
            return Detection(class_name=class_name, confidence=confidence, bbox=bbox, area_ratio=area_ratio)

    raise ValueError(f"Unable to normalize detection format: {raw}")


def score_to_severity_level(score: int, config: Optional[Dict[str, Any]] = None) -> SeverityLevel:
    """Maps a 0-100 numerical pollution score to a qualitative SeverityLevel."""
    cfg = config or SEVERITY_CONFIG
    thresholds = cfg["thresholds"]

    if score <= thresholds["clean"]:
        return SeverityLevel.CLEAN
    if score >= thresholds["critical"]:
        return SeverityLevel.CRITICAL
    if score >= thresholds["high"]:
        return SeverityLevel.HIGH
    if score >= thresholds["moderate"]:
        return SeverityLevel.MODERATE
    return SeverityLevel.LOW


def calculate_severity(
    detections: List[Union[Detection, Dict[str, Any], Tuple[Any, ...]]],
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[SeverityLevel, int, Dict[str, Any]]:
    """
    Calculates the visual pollution score (0-100), severity level, and component breakdown.

    Parameters:
      - detections: List of standardized or raw detections
      - image_width: Optional image width in pixels (helps compute area_ratio from bbox if missing)
      - image_height: Optional image height in pixels
      - config: Optional custom scoring configuration override

    Returns:
      (SeverityLevel, severity_score [0-100], score_breakdown dict)
    """
    cfg = config or SEVERITY_CONFIG
    weights = cfg["component_weights"]
    count_sat = cfg["count_saturation"]
    cov_sat = cfg["coverage_saturation"]

    # 1. Graceful empty / zero detections handling
    if not detections:
        breakdown = {
            "count_score": 0.0,
            "avg_conf_score": 0.0,
            "max_conf_score": 0.0,
            "coverage_score": 0.0,
            "raw_total": 0.0,
            "final_score": 0,
            "total_detections": 0,
            "average_confidence": 0.0,
            "max_confidence": 0.0,
            "estimated_coverage": 0.0,
            "used_area_ratio": False,
        }
        return SeverityLevel.CLEAN, 0, breakdown

    # 2. Normalize all detections
    normalized: List[Detection] = []
    for d in detections:
        try:
            normalized.append(normalize_detection(d))
        except Exception:
            continue  # Skip unparseable single detection rather than failing entire analysis

    if not normalized:
        return SeverityLevel.CLEAN, 0, {"final_score": 0, "total_detections": 0}

    total_count = len(normalized)

    # 3. Class-weighted count calculation
    weighted_count = 0.0
    confidences: List[float] = []
    area_ratios: List[float] = []

    for det in normalized:
        cls_weight = cfg["class_weights"].get(det.class_name.lower(), cfg["class_weights"].get("default", 1.0))
        weighted_count += cls_weight
        confidences.append(det.confidence)

        # Handle area_ratio
        if det.area_ratio is not None and det.area_ratio > 0.0:
            area_ratios.append(det.area_ratio)
        elif image_width and image_height and det.bbox and len(det.bbox) == 4:
            # Estimate area_ratio from bounding box if image dimensions are supplied
            w = max(0.0, det.bbox[2] - det.bbox[0])
            h = max(0.0, det.bbox[3] - det.bbox[1])
            est_area = (w * h) / (image_width * image_height)
            area_ratios.append(min(1.0, max(0.0, est_area)))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    max_conf = max(confidences) if confidences else 0.0

    # 4. Component 1: Detection Count Score (0 - weights["detection_count"])
    # Logarithmic scaling for realistic saturation
    count_factor = min(1.0, math.log1p(weighted_count) / math.log1p(count_sat))
    count_score = count_factor * weights["detection_count"]

    # 5. Component 2: Average Confidence Score (0 - weights["avg_confidence"])
    avg_conf_score = avg_conf * weights["avg_confidence"]

    # 6. Component 3: Maximum Confidence Score (0 - weights["max_confidence"])
    max_conf_score = max_conf * weights["max_confidence"]

    # 7. Component 4: Coverage / Density Score (0 - weights["coverage_or_density"])
    used_area_ratio = len(area_ratios) > 0
    if used_area_ratio:
        # Sum of area ratios (capped at 1.0)
        total_cov = min(1.0, sum(area_ratios))
        coverage_factor = min(1.0, total_cov / cov_sat)
        coverage_score = coverage_factor * weights["coverage_or_density"]
        estimated_coverage = round(total_cov, 4)
    else:
        # Density fallback when area_ratio is unavailable
        # Uses count density scaled with average confidence
        density_factor = min(1.0, (total_count / 8.0) * (0.5 + 0.5 * avg_conf))
        coverage_score = density_factor * weights["coverage_or_density"]
        estimated_coverage = None

    # 8. Composite calculation
    raw_total = count_score + avg_conf_score + max_conf_score + coverage_score
    # Clamp strictly to 1 - 100 for non-empty images
    final_score = int(round(min(100.0, max(1.0, raw_total))))
    severity_level = score_to_severity_level(final_score, cfg)

    breakdown = {
        "count_score": round(count_score, 2),
        "avg_conf_score": round(avg_conf_score, 2),
        "max_conf_score": round(max_conf_score, 2),
        "coverage_score": round(coverage_score, 2),
        "raw_total": round(raw_total, 2),
        "final_score": final_score,
        "total_detections": total_count,
        "average_confidence": round(avg_conf, 4),
        "max_confidence": round(max_conf, 4),
        "estimated_coverage": estimated_coverage,
        "used_area_ratio": used_area_ratio,
        "severity_level": severity_level.value,
    }

    return severity_level, final_score, breakdown
