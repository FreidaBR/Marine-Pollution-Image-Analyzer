"""
Trend Analysis and Time-Series Analytics Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Computes temporal trends, percentage trajectories, and frontend-ready
time-series arrays for charting and environmental monitoring.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from reporting.schemas import TrendSeries, AnalysisResult, SurveyResult


def calculate_trends(items: List[Any]) -> TrendSeries:
    """
    Computes time-series metrics across a chronological sequence of analyses or surveys.
    Returns a frontend-friendly TrendSeries model.
    """
    if not items:
        return TrendSeries(
            dates=[],
            scores=[],
            detection_counts=[],
            severity_levels=[],
            dominant_categories=[],
            trend_direction="stable",
            percentage_change=0.0,
            recent_change=0.0,
            highest_risk_period=None,
        )

    # 1. Parse chronological entries
    entries = []
    for idx, item in enumerate(items):
        if isinstance(item, SurveyResult):
            date_str = item.date or f"Survey-{idx+1}"
            score = item.average_score
            dets = item.total_detections
            sev = item.overall_severity.value
            cat = item.dominant_category
        elif isinstance(item, AnalysisResult):
            date_str = item.timestamp or f"Analysis-{idx+1}"
            score = item.summary.severity_score
            dets = item.summary.total_detections
            sev = item.summary.severity.value
            cat = item.summary.dominant_category
        elif isinstance(item, dict):
            date_str = str(item.get("date") or item.get("timestamp") or f"Point-{idx+1}")
            score = int(item.get("score") or item.get("severity_score") or item.get("average_score", 0))
            dets = int(item.get("detections") or item.get("total_detections", 0))
            sev = str(item.get("severity") or item.get("overall_severity", "Low"))
            cat = str(item.get("dominant_category") or "marine_debris")
        else:
            continue

        entries.append({
            "date": date_str,
            "score": score,
            "detections": dets,
            "severity": sev,
            "category": cat,
        })

    if not entries:
        return TrendSeries(
            dates=[],
            scores=[],
            detection_counts=[],
            severity_levels=[],
            dominant_categories=[],
            trend_direction="stable",
            percentage_change=0.0,
            recent_change=0.0,
            highest_risk_period=None,
        )

    dates = [e["date"] for e in entries]
    scores = [e["score"] for e in entries]
    detection_counts = [e["detections"] for e in entries]
    severity_levels = [e["severity"] for e in entries]
    dominant_categories = [e["category"] for e in entries]

    # Overall percentage change from earliest to latest
    first_score = scores[0]
    last_score = scores[-1]
    if first_score > 0:
        pct_change = round(((last_score - first_score) / first_score) * 100.0, 2)
    else:
        pct_change = 100.0 if last_score > 0 else 0.0

    # Recent change (between second-to-last and last, if available)
    if len(scores) >= 2:
        penultimate = scores[-2]
        if penultimate > 0:
            recent_change = round(((last_score - penultimate) / penultimate) * 100.0, 2)
        else:
            recent_change = 100.0 if last_score > 0 else 0.0
    else:
        recent_change = pct_change

    # Overall direction
    if pct_change > 5.0 or (last_score - first_score) > 3:
        direction = "deteriorating"
    elif pct_change < -5.0 or (last_score - first_score) < -3:
        direction = "improving"
    else:
        direction = "stable"

    # Identify highest-risk period
    max_idx = scores.index(max(scores))
    highest_risk_period = dates[max_idx]

    return TrendSeries(
        dates=dates,
        scores=scores,
        detection_counts=detection_counts,
        severity_levels=severity_levels,
        dominant_categories=dominant_categories,
        trend_direction=direction,
        percentage_change=pct_change,
        recent_change=recent_change,
        highest_risk_period=highest_risk_period,
    )
