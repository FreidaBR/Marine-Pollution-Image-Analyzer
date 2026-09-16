"""
Standardized Data Schemas & Contracts for Marine Pollution Image Analyzer.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Provides Pydantic models and serialization contracts for model detections,
severity evaluations, survey aggregations, historical trends, location clusters,
recommendations, and report payloads.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    CLEAN = "Clean"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class Detection(BaseModel):
    """Standardized representation of a single visual pollution detection."""
    class_name: str = Field(default="marine_debris", description="Detected category name")
    confidence: float = Field(default=0.5, description="Confidence score from model [0.0 - 1.0]")
    bbox: List[float] = Field(description="Bounding box [x_min, y_min, x_max, y_max]")
    area_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Estimated bbox area / image area [0.0 - 1.0]")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
        except Exception:
            val = 0.5
        if val < 0.0:
            return 0.0
        if val > 1.0:
            return 1.0
        return round(val, 4)

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError("Bounding box must contain exactly 4 values: [x_min, y_min, x_max, y_max]")
        return [float(x) for x in v]


class Location(BaseModel):
    """Geographic and temporal metadata for an observation or survey."""
    name: Optional[str] = Field(default="Unknown Location", description="Descriptive place name")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Latitude [-90 to 90]")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Longitude [-180 to 180]")
    observation_date: Optional[str] = Field(default=None, description="ISO 8601 formatted date/time")


class AnalysisSummary(BaseModel):
    """Consolidated visual assessment summary for a single analyzed image."""
    dominant_category: str = Field(default="marine_debris")
    total_detections: int = Field(ge=0)
    severity: SeverityLevel = Field(default=SeverityLevel.LOW)
    severity_score: int = Field(ge=0, le=100, description="Visual pollution score [0 - 100]")
    average_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    max_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_coverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    waste_composition: Dict[str, float] = Field(default_factory=dict, description="Percentage makeup of detected waste classes")
    ecological_risk: str = Field(default="Unknown", description="Assessed risk tier (Low, Moderate, High, Critical)")
    ecological_concerns: List[str] = Field(default_factory=list, description="Primary environmental concerns")
    ecological_reasoning: str = Field(default="", description="Rule-based reasoning for the risk assessment")



class AnalysisResult(BaseModel):
    """Standardized single-image analysis structure consumable by frontend & reporting."""
    analysis_id: str
    status: str = Field(default="completed")
    image_url: Optional[str] = None
    timestamp: Optional[str] = None
    location: Optional[Location] = None
    detections: List[Detection] = Field(default_factory=list)
    summary: AnalysisSummary
    report_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SurveyResult(BaseModel):
    """Aggregated analysis representing a multi-image coastal survey."""
    survey_id: str
    survey_name: str
    date: Optional[str] = None
    total_images: int
    affected_images: int
    clean_images: int
    total_detections: int
    average_detections_per_image: float
    average_confidence: float
    highest_confidence: float
    average_score: int
    overall_severity: SeverityLevel
    dominant_category: str
    severity_distribution: Dict[str, int]
    images: List[AnalysisResult] = Field(default_factory=list)
    location_summary: Optional[Dict[str, Any]] = None


class HistoryComparison(BaseModel):
    """Delta comparison between two surveys or time periods."""
    previous_id: str
    current_id: str
    previous_score: int
    current_score: int
    score_change: int
    score_percent_change: float
    detection_count_change: int
    detection_percent_change: float
    severity_previous: SeverityLevel
    severity_current: SeverityLevel
    severity_changed: bool
    trend_direction: str  # "deteriorating", "improving", "stable"
    summary_text: str


class LocationCluster(BaseModel):
    """Location metrics and hotspot indicator."""
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    analysis_count: int
    total_detections: int
    average_score: int
    severity: SeverityLevel
    is_hotspot: bool = False
    risk_rank: Optional[int] = None


class TrendSeries(BaseModel):
    """Frontend-ready time-series structure for trend rendering."""
    dates: List[str]
    scores: List[int]
    detection_counts: List[int]
    severity_levels: List[str]
    dominant_categories: List[str]
    trend_direction: str
    percentage_change: float
    recent_change: float
    highest_risk_period: Optional[str] = None


class Recommendation(BaseModel):
    """Actionable guidance tiered by visual pollution severity."""
    level: SeverityLevel
    primary_action: str
    suggested_actions: List[str]
    urgency: str
    authority_notification_recommended: bool
    disclaimer: str = (
        "Assessment is based on visible image indicators only and does not reflect laboratory chemical analysis."
    )


class ReportData(BaseModel):
    """Structured report payload ready for export or preview rendering."""
    report_id: str
    generated_at: str
    target_type: str  # "single_image" or "survey"
    title: str
    location: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    metrics: Dict[str, Any]
    detections_summary: Dict[str, Any]
    severity_assessment: Dict[str, Any]
    trend_summary: Optional[Dict[str, Any]] = None
    hotspot_status: Optional[Dict[str, Any]] = None
    recommendations: Recommendation
    disclaimer: str
