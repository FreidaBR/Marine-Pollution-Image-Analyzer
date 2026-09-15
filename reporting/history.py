"""
Historical Tracking and Delta Comparison Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Compares historical observations and surveys to measure trends,
percentage changes in pollution scores, detection spikes, and severity transitions.
"""

from __future__ import annotations
from typing import Union, Dict, Any, Optional
from reporting.schemas import (
    SeverityLevel,
    HistoryComparison,
    AnalysisResult,
    SurveyResult,
)


def compare_historical_points(
    previous: Union[AnalysisResult, SurveyResult, Dict[str, Any]],
    current: Union[AnalysisResult, SurveyResult, Dict[str, Any]],
) -> HistoryComparison:
    """
    Compares two analytical data points (either two individual analyses or two multi-image surveys).
    """
    # Extract previous metrics
    if isinstance(previous, SurveyResult):
        prev_id = previous.survey_id
        prev_score = previous.average_score
        prev_count = previous.total_detections
        prev_sev = previous.overall_severity
    elif isinstance(previous, AnalysisResult):
        prev_id = previous.analysis_id
        prev_score = previous.summary.severity_score
        prev_count = previous.summary.total_detections
        prev_sev = previous.summary.severity
    else:
        prev_id = str(previous.get("observation_id") or previous.get("id") or previous.get("survey_id") or previous.get("analysis_id", "PREV"))
        prev_sum = previous.get("summary") if isinstance(previous.get("summary"), dict) else {}
        prev_score = int(prev_sum.get("severity_score") or previous.get("score") or previous.get("severity_score") or previous.get("average_score", 0))
        
        raw_dets = previous.get("detections")
        if isinstance(raw_dets, list):
            prev_count = len(raw_dets)
        else:
            prev_count = int(prev_sum.get("total_detections") or raw_dets or previous.get("total_detections", 0))
            
        raw_sev = prev_sum.get("severity") or previous.get("severity") or previous.get("overall_severity", "Low")
        prev_sev = SeverityLevel(raw_sev) if raw_sev in [s.value for s in SeverityLevel] else SeverityLevel.LOW

    # Extract current metrics
    if isinstance(current, SurveyResult):
        curr_id = current.survey_id
        curr_score = current.average_score
        curr_count = current.total_detections
        curr_sev = current.overall_severity
    elif isinstance(current, AnalysisResult):
        curr_id = current.analysis_id
        curr_score = current.summary.severity_score
        curr_count = current.summary.total_detections
        curr_sev = current.summary.severity
    else:
        curr_id = str(current.get("observation_id") or current.get("id") or current.get("survey_id") or current.get("analysis_id", "CURR"))
        curr_sum = current.get("summary") if isinstance(current.get("summary"), dict) else {}
        curr_score = int(curr_sum.get("severity_score") or current.get("score") or current.get("severity_score") or current.get("average_score", 0))
        
        raw_curr_dets = current.get("detections")
        if isinstance(raw_curr_dets, list):
            curr_count = len(raw_curr_dets)
        else:
            curr_count = int(curr_sum.get("total_detections") or raw_curr_dets or current.get("total_detections", 0))
            
        raw_curr_sev = curr_sum.get("severity") or current.get("severity") or current.get("overall_severity", "Low")
        curr_sev = SeverityLevel(raw_curr_sev) if raw_curr_sev in [s.value for s in SeverityLevel] else SeverityLevel.LOW

    score_change = curr_score - prev_score
    if prev_score > 0:
        score_pct_change = round(((curr_score - prev_score) / prev_score) * 100.0, 2)
    else:
        score_pct_change = 100.0 if curr_score > 0 else 0.0

    count_change = curr_count - prev_count
    if prev_count > 0:
        count_pct_change = round(((curr_count - prev_count) / prev_count) * 100.0, 2)
    else:
        count_pct_change = 100.0 if curr_count > 0 else 0.0

    # Determine trend direction
    if score_change > 3 or count_change > 1:
        trend_direction = "deteriorating"
    elif score_change < -3 or count_change < -1:
        trend_direction = "improving"
    else:
        trend_direction = "stable"

    severity_changed = (prev_sev != curr_sev)

    # Human-readable summary
    parts = []
    if score_change > 0:
        parts.append(f"Pollution score increased by {abs(score_pct_change):.1f}% (+{score_change} pts)")
    elif score_change < 0:
        parts.append(f"Pollution score decreased by {abs(score_pct_change):.1f}% ({score_change} pts)")
    else:
        parts.append("Pollution score remained unchanged")

    if count_change != 0:
        sign = "+" if count_change > 0 else ""
        parts.append(f"detection count changed by {sign}{count_change} ({count_pct_change:+.1f}%)")

    if severity_changed:
        parts.append(f"Severity transitioned from {prev_sev.value} → {curr_sev.value}")
    else:
        parts.append(f"Severity remained {curr_sev.value}")

    summary_text = " · ".join(parts)

    return HistoryComparison(
        previous_id=prev_id,
        current_id=curr_id,
        previous_score=prev_score,
        current_score=curr_score,
        score_change=score_change,
        score_percent_change=score_pct_change,
        detection_count_change=count_change,
        detection_percent_change=count_pct_change,
        severity_previous=prev_sev,
        severity_current=curr_sev,
        severity_changed=severity_changed,
        trend_direction=trend_direction,
        summary_text=summary_text,
    )
