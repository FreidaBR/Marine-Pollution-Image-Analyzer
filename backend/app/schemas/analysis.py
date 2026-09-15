"""Pydantic schemas implementing the frozen API contract in
docs/api-contract.md. Field names, nesting, and casing here are load-bearing —
the frontend and reporting teammates build against this shape. Don't rename
without updating that doc and telling the team.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationIn(BaseModel):
    """Optional location fields accepted alongside the uploaded image."""

    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    observation_date: str | None = None  # ISO 8601 date/datetime string


class LocationOut(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class DetectionOut(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float]  # [x_min, y_min, x_max, y_max]
    area_ratio: float = 0.0


class AnalysisSummaryOut(BaseModel):
    dominant_category: str
    total_detections: int
    severity: str  # "Low" | "Moderate" | "High" | "Critical"
    severity_score: int  # 0-100


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str = "completed"
    image_url: str
    location: LocationOut | None = None
    detections: list[DetectionOut]
    summary: AnalysisSummaryOut
    report_url: str


class AnalysisListItem(BaseModel):
    analysis_id: str
    image_url: str
    created_at: datetime.datetime
    summary: AnalysisSummaryOut


class AnalysisListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AnalysisListItem]


class ReportResponse(BaseModel):
    """GET /api/v1/reports/{analysis_id}.

    Prefers `reporting.report_builder` once implemented (see
    app/services/report_service.py); this is the fallback shape.
    """

    analysis_id: str
    generated_at: datetime.datetime
    image_name: str
    location: LocationOut | None = None
    detections: list[DetectionOut]
    severity: str
    severity_score: int
    recommendations: list[str]
    disclaimer: str = Field(
        default=(
            "This report reflects visible-indicator estimates from image analysis, "
            "not laboratory-confirmed contamination."
        )
    )


class HealthStatus(BaseModel):
    status: str = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error: ErrorDetail
