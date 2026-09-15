"""Builds the report returned by GET /api/v1/reports/{analysis_id}.

Prefers the teammate-owned `reporting.report_builder` implementation once it
exists. Falls back to a basic JSON report (no PDF/HTML yet — that's Member
4's deliverable) so the endpoint in the frozen contract works today.

Contract `reporting.report_builder` should satisfy, if/when implemented:

    def build_report(analysis: dict) -> dict:
        '''analysis: {"analysis_id", "image_name", "location", "detections",
        "severity", "severity_score", "created_at"}.
        Returns a dict with at least: "recommendations": list[str], plus
        whatever extra report fields reporting/report_builder.py adds
        (e.g. HTML/PDF export links).'''
"""

from __future__ import annotations

from app.models.analysis import Analysis
from app.schemas.analysis import DetectionOut, LocationOut, ReportResponse

_RECOMMENDATIONS_BY_SEVERITY = {
    "Low": ["Monitor and document the site for future reference."],
    "Moderate": ["Inspect the area in person and consider a cleanup effort."],
    "High": ["Prioritize field verification of this location soon."],
    "Critical": ["Notify the responsible environmental authority and verify immediately."],
}


def _fallback_recommendations(severity: str) -> list[str]:
    return _RECOMMENDATIONS_BY_SEVERITY.get(severity, _RECOMMENDATIONS_BY_SEVERITY["Low"])


def build_report(analysis: Analysis, detections: list[DetectionOut]) -> ReportResponse:
    location = None
    if analysis.location_name or analysis.latitude is not None:
        location = LocationOut(
            name=analysis.location_name,
            latitude=analysis.latitude,
            longitude=analysis.longitude,
        )

    try:
        from reporting.report_builder import build_report as real_build_report
    except Exception:
        recommendations = _fallback_recommendations(analysis.severity)
    else:
        raw = real_build_report(
            {
                "analysis_id": analysis.public_id,
                "image_name": analysis.image.filename,
                "location": location.model_dump() if location else None,
                "detections": [d.model_dump() for d in detections],
                "severity": analysis.severity,
                "severity_score": analysis.severity_score,
                "created_at": analysis.created_at.isoformat(),
            }
        )
        recommendations = raw.get("recommendations") or _fallback_recommendations(analysis.severity)

    return ReportResponse(
        analysis_id=analysis.public_id,
        generated_at=analysis.created_at,
        image_name=analysis.image.filename,
        location=location,
        detections=detections,
        severity=analysis.severity,
        severity_score=analysis.severity_score,
        recommendations=recommendations,
    )
