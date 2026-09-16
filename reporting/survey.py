"""
Multi-Image Survey Aggregation Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Aggregates multiple individual image analyses into a cohesive coastal survey assessment,
supporting multi-image missions, aerial drone transects, and shoreline patrols.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from collections import Counter
from reporting.schemas import (
    SeverityLevel,
    AnalysisResult,
    SurveyResult,
)
from reporting.severity import score_to_severity_level
from reporting.analytics import calculate_severity_distribution


def calculate_survey_statistics(analyses: List[AnalysisResult]) -> Dict[str, Any]:
    """Computes detailed statistical breakdown for a set of survey images."""
    total_images = len(analyses)
    if total_images == 0:
        return {
            "total_images": 0,
            "affected_images": 0,
            "clean_images": 0,
            "total_detections": 0,
            "average_detections_per_image": 0.0,
            "average_confidence": 0.0,
            "highest_confidence": 0.0,
            "average_score": 0,
            "dominant_category": "None",
            "severity_distribution": {k.value: 0 for k in SeverityLevel},
        }

    total_detections = sum(a.summary.total_detections for a in analyses)
    affected_images = sum(1 for a in analyses if a.summary.total_detections > 0)
    clean_images = total_images - affected_images

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

    return {
        "total_images": total_images,
        "affected_images": affected_images,
        "clean_images": clean_images,
        "total_detections": total_detections,
        "average_detections_per_image": round(total_detections / total_images, 2),
        "average_confidence": round(avg_conf, 4),
        "highest_confidence": round(highest_conf, 4),
        "average_score": avg_score,
        "dominant_category": dominant_cat,
        "severity_distribution": calculate_severity_distribution(analyses),
    }


def calculate_survey_severity(analyses: List[AnalysisResult]) -> Tuple[SeverityLevel, int]:
    """
    Computes overall survey severity and representative composite score.
    Weights both the average pollution across the survey area and the peak critical hotspots.
    """
    if not analyses:
        return SeverityLevel.CLEAN, 0

    scores = [a.summary.severity_score for a in analyses]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)

    # 70% weight to area-wide average, 30% weight to peak focal hot zone
    composite_score = int(round((0.70 * avg_score) + (0.30 * max_score)))
    composite_score = min(100, max(0, composite_score))

    severity_level = score_to_severity_level(composite_score)
    return severity_level, composite_score


def aggregate_survey(
    survey_id: str,
    survey_name: str,
    analyses: List[AnalysisResult],
    date: Optional[str] = None,
    location_summary: Optional[Dict[str, Any]] = None,
) -> SurveyResult:
    """
    Aggregates an entire multi-image survey into a standardized SurveyResult.
    Handles images with or without geographic coordinates.
    """
    stats = calculate_survey_statistics(analyses)
    overall_sev, avg_score = calculate_survey_severity(analyses)

    # Extract common location metadata if not explicitly provided
    if location_summary is None and analyses:
        valid_locs = [a.location.name for a in analyses if a.location and a.location.name]
        loc_name = valid_locs[0] if valid_locs else "Coastal Survey Transect"
        coords = [
            (a.location.latitude, a.location.longitude)
            for a in analyses
            if a.location and a.location.latitude is not None and a.location.longitude is not None
        ]
        avg_lat = sum(c[0] for c in coords) / len(coords) if coords else None
        avg_lon = sum(c[1] for c in coords) / len(coords) if coords else None

        location_summary = {
            "name": loc_name,
            "latitude": round(avg_lat, 4) if avg_lat is not None else None,
            "longitude": round(avg_lon, 4) if avg_lon is not None else None,
            "georeferenced_images": len(coords),
        }

    return SurveyResult(
        survey_id=survey_id,
        survey_name=survey_name,
        date=date,
        total_images=stats["total_images"],
        affected_images=stats["affected_images"],
        clean_images=stats["clean_images"],
        total_detections=stats["total_detections"],
        average_detections_per_image=stats["average_detections_per_image"],
        average_confidence=stats["average_confidence"],
        highest_confidence=stats["highest_confidence"],
        average_score=avg_score,
        overall_severity=overall_sev,
        dominant_category=stats["dominant_category"],
        severity_distribution=stats["severity_distribution"],
        images=analyses,
        location_summary=location_summary,
    )
