"""
Reporting, Analytics & Environmental Intelligence Package.
Marine Pollution Image Analyzer - Role 4.
"""

from reporting.schemas import (
    SeverityLevel,
    Detection,
    Location,
    AnalysisSummary,
    AnalysisResult,
    SurveyResult,
    HistoryComparison,
    LocationCluster,
    TrendSeries,
    Recommendation,
    ReportData,
)
from reporting.severity import (
    SEVERITY_CONFIG,
    calculate_severity,
    normalize_detection,
    score_to_severity_level,
)
from reporting.analytics import (
    analyze_single_result,
    calculate_dataset_statistics,
    calculate_severity_distribution,
    identify_dominant_category,
)
from reporting.survey import (
    aggregate_survey,
    calculate_survey_severity,
    calculate_survey_statistics,
)
from reporting.history import compare_historical_points
from reporting.hotspots import aggregate_location_intelligence, haversine_distance_km
from reporting.trends import calculate_trends
from reporting.recommendations import get_recommendations
from reporting.report_builder import (
    build_analysis_report,
    build_survey_report,
    render_html_report,
)

__all__ = [
    "SeverityLevel",
    "Detection",
    "Location",
    "AnalysisSummary",
    "AnalysisResult",
    "SurveyResult",
    "HistoryComparison",
    "LocationCluster",
    "TrendSeries",
    "Recommendation",
    "ReportData",
    "SEVERITY_CONFIG",
    "calculate_severity",
    "normalize_detection",
    "score_to_severity_level",
    "analyze_single_result",
    "calculate_dataset_statistics",
    "calculate_severity_distribution",
    "identify_dominant_category",
    "aggregate_survey",
    "calculate_survey_severity",
    "calculate_survey_statistics",
    "compare_historical_points",
    "aggregate_location_intelligence",
    "haversine_distance_km",
    "calculate_trends",
    "get_recommendations",
    "build_analysis_report",
    "build_survey_report",
    "render_html_report",
]
