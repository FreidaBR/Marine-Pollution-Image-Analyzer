"""
Analytics & Statistics Engine for Marine Pollution Observations.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Computes analytical metrics, distributions, affected rates, and aggregations
across individual images and multi-image datasets.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from collections import Counter
from reporting.schemas import (
    SeverityLevel,
    Detection,
    AnalysisResult,
    AnalysisSummary,
    Location,
)
from reporting.severity import calculate_severity, normalize_detection


def analyze_single_result(
    analysis_id: str,
    detections: List[Any],
    image_url: Optional[str] = None,
    location: Optional[Location] = None,
    timestamp: Optional[str] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """
    Constructs a complete standardized AnalysisResult from raw detections and image metadata.
    """
    normalized_dets = [normalize_detection(d) for d in detections]
    severity_level, score, breakdown = calculate_severity(
        normalized_dets,
        image_width=image_width,
        image_height=image_height,
    )

    dominant_cat = identify_dominant_category(normalized_dets)

    summary = AnalysisSummary(
        dominant_category=dominant_cat,
        total_detections=len(normalized_dets),
        severity=severity_level,
        severity_score=score,
        average_confidence=breakdown.get("average_confidence", 0.0),
        max_confidence=breakdown.get("max_confidence", 0.0),
        estimated_coverage=breakdown.get("estimated_coverage"),
    )

    return AnalysisResult(
        analysis_id=analysis_id,
        status="completed",
        image_url=image_url or f"/uploads/{analysis_id}.jpg",
        timestamp=timestamp,
        location=location,
        detections=normalized_dets,
        summary=summary,
        report_url=f"/api/v1/reports/{analysis_id}",
        metadata=metadata or {},
    )


def identify_dominant_category(detections: List[Detection]) -> str:
    """Finds the most frequently detected pollution class among detections."""
    if not detections:
        return "None"
    counts = Counter(d.class_name for d in detections)
    return counts.most_common(1)[0][0]


def calculate_severity_distribution(analyses: List[AnalysisResult]) -> Dict[str, int]:
    """Calculates distribution counts across Clean, Low, Moderate, High, Critical."""
    dist: Dict[str, int] = {
        SeverityLevel.CLEAN.value: 0,
        SeverityLevel.LOW.value: 0,
        SeverityLevel.MODERATE.value: 0,
        SeverityLevel.HIGH.value: 0,
        SeverityLevel.CRITICAL.value: 0,
    }
    for a in analyses:
        sev = a.summary.severity.value if hasattr(a.summary.severity, "value") else str(a.summary.severity)
        if sev in dist:
            dist[sev] += 1
        else:
            dist[sev] = 1
    return dist


def calculate_dataset_statistics(analyses: List[AnalysisResult]) -> Dict[str, Any]:
    """
    Computes high-level aggregated intelligence metrics across a collection of analyses.
    """
    total_images = len(analyses)
    if total_images == 0:
        return {
            "total_analyses": 0,
            "total_detections": 0,
            "average_detections_per_image": 0.0,
            "average_confidence": 0.0,
            "highest_confidence": 0.0,
            "average_pollution_score": 0,
            "current_severity": SeverityLevel.CLEAN.value,
            "affected_images": 0,
            "clean_images": 0,
            "affected_ratio": 0.0,
            "dominant_category": "None",
            "severity_distribution": {k.value: 0 for k in SeverityLevel},
            "highest_severity_observation": None,
            "locations_monitored_count": 0,
            "unique_locations": [],
        }

    total_detections = sum(a.summary.total_detections for a in analyses)
    affected_analyses = [a for a in analyses if a.summary.total_detections > 0]
    affected_count = len(affected_analyses)
    clean_count = total_images - affected_count

    all_confidences = [
        d.confidence
        for a in analyses
        for d in a.detections
    ]
    avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    highest_conf = max(all_confidences) if all_confidences else 0.0

    scores = [a.summary.severity_score for a in analyses]
    avg_score = int(round(sum(scores) / total_images)) if scores else 0

    all_categories = [
        d.class_name
        for a in analyses
        for d in a.detections
    ]
    dominant_cat = Counter(all_categories).most_common(1)[0][0] if all_categories else "marine_debris"

    # Current overall severity level determined by the average score and worst-case peaks
    from reporting.severity import score_to_severity_level
    current_severity = score_to_severity_level(avg_score).value

    # Highest severity observation
    highest_obs = max(analyses, key=lambda a: a.summary.severity_score) if analyses else None
    highest_severity_info = {
        "analysis_id": highest_obs.analysis_id,
        "location": highest_obs.location.name if highest_obs and highest_obs.location else "Unknown",
        "score": highest_obs.summary.severity_score if highest_obs else 0,
        "severity": highest_obs.summary.severity.value if highest_obs and hasattr(highest_obs.summary.severity, "value") else (str(highest_obs.summary.severity) if highest_obs else "Clean"),
        "timestamp": highest_obs.timestamp if highest_obs else None,
    } if highest_obs else None

    # Distinct locations monitored
    unique_locations = set(
        a.location.name for a in analyses if a.location and a.location.name
    )

    return {
        "total_analyses": total_images,
        "total_detections": total_detections,
        "average_detections_per_image": round(total_detections / total_images, 2),
        "average_confidence": round(avg_conf, 4),
        "highest_confidence": round(highest_conf, 4),
        "average_pollution_score": avg_score,
        "current_severity": current_severity,
        "affected_images": affected_count,
        "clean_images": clean_count,
        "affected_ratio": round(affected_count / total_images, 4),
        "dominant_category": dominant_cat,
        "severity_distribution": calculate_severity_distribution(analyses),
        "highest_severity_observation": highest_severity_info,
        "locations_monitored_count": len(unique_locations),
        "unique_locations": sorted(list(unique_locations)),
    }
