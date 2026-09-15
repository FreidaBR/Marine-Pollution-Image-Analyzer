"""
Report Builder and Export Data Generator.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Generates structured report JSON payloads and print/export-ready HTML reports
following the MarineGuard AI ocean design system.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Union, Optional, Dict, Any
from reporting.schemas import (
    ReportData,
    AnalysisResult,
    SurveyResult,
    SeverityLevel,
)
from reporting.recommendations import get_recommendations


def build_analysis_report(
    analysis: AnalysisResult,
    historical_delta: Optional[Dict[str, Any]] = None,
    is_hotspot: bool = False,
) -> ReportData:
    """Creates a comprehensive structured report for an individual image analysis."""
    now_iso = datetime.now(timezone.utc).isoformat()
    recs = get_recommendations(analysis.summary.severity)

    coords = None
    loc_name = "Unknown Location"
    if analysis.location:
        loc_name = analysis.location.name or loc_name
        if analysis.location.latitude is not None and analysis.location.longitude is not None:
            coords = {"latitude": analysis.location.latitude, "longitude": analysis.location.longitude}

    return ReportData(
        report_id=f"REP-{analysis.analysis_id}",
        generated_at=now_iso,
        target_type="single_image",
        title=f"Visible Pollution Report: {analysis.analysis_id}",
        location=loc_name,
        coordinates=coords,
        metrics={
            "analysis_id": analysis.analysis_id,
            "image_url": analysis.image_url,
            "total_images": 1,
            "total_detections": analysis.summary.total_detections,
            "average_confidence": analysis.summary.average_confidence,
            "max_confidence": analysis.summary.max_confidence,
            "estimated_coverage": analysis.summary.estimated_coverage,
        },
        detections_summary={
            "dominant_category": analysis.summary.dominant_category,
            "total_count": analysis.summary.total_detections,
            "detections": [d.model_dump() for d in analysis.detections],
        },
        severity_assessment={
            "severity_score": analysis.summary.severity_score,
            "severity_level": analysis.summary.severity.value,
            "status": "Completed",
        },
        trend_summary=historical_delta,
        hotspot_status={"is_hotspot": is_hotspot},
        recommendations=recs,
        disclaimer=(
            "This analysis identifies visible marine-debris indicators from the submitted image. "
            "It is not a laboratory or chemical contamination assessment."
        ),
    )


def build_survey_report(
    survey: SurveyResult,
    historical_delta: Optional[Dict[str, Any]] = None,
    hotspot_summary: Optional[Dict[str, Any]] = None,
) -> ReportData:
    """Creates a comprehensive structured report for an entire coastal survey."""
    now_iso = datetime.now(timezone.utc).isoformat()
    recs = get_recommendations(survey.overall_severity)

    coords = None
    loc_name = survey.survey_name
    if survey.location_summary:
        loc_name = survey.location_summary.get("name") or loc_name
        lat = survey.location_summary.get("latitude")
        lon = survey.location_summary.get("longitude")
        if lat is not None and lon is not None:
            coords = {"latitude": lat, "longitude": lon}

    return ReportData(
        report_id=f"REP-{survey.survey_id}",
        generated_at=now_iso,
        target_type="survey",
        title=f"Coastal Survey Assessment Report: {survey.survey_name}",
        location=loc_name,
        coordinates=coords,
        metrics={
            "survey_id": survey.survey_id,
            "survey_date": survey.date,
            "total_images": survey.total_images,
            "affected_images": survey.affected_images,
            "clean_images": survey.clean_images,
            "total_detections": survey.total_detections,
            "average_detections_per_image": survey.average_detections_per_image,
            "average_confidence": survey.average_confidence,
            "highest_confidence": survey.highest_confidence,
            "average_score": survey.average_score,
        },
        detections_summary={
            "dominant_category": survey.dominant_category,
            "total_count": survey.total_detections,
            "severity_distribution": survey.severity_distribution,
        },
        severity_assessment={
            "composite_score": survey.average_score,
            "severity_level": survey.overall_severity.value,
            "status": "Completed",
        },
        trend_summary=historical_delta,
        hotspot_status=hotspot_summary,
        recommendations=recs,
        disclaimer=(
            "DISCLAIMER: This assessment is based exclusively on visible image indicators detected by computer vision. "
            "It does NOT constitute chemical, microbiological, or laboratory-confirmed water quality analysis."
        ),
    )


def render_html_report(report: ReportData) -> str:
    """
    Renders an executive printable HTML report styled in the MarineGuard AI ocean aesthetic.
    Self-contained, uses Google Fonts and Tailwind CDN.
    """
    badge_colors = {
        "Clean": "bg-secondary-container/20 text-secondary-container border-secondary-container/30",
        "Low": "bg-primary-fixed-dim/20 text-primary-fixed-dim border-primary-fixed-dim/30",
        "Moderate": "bg-amber-400/20 text-amber-300 border-amber-400/30",
        "High": "bg-orange-500/20 text-orange-300 border-orange-500/30",
        "Critical": "bg-error-container/40 text-error border-error/50",
    }
    sev_level = report.severity_assessment.get("severity_level", "Low")
    badge_cls = badge_colors.get(sev_level, badge_colors["Low"])

    coords_str = ""
    if report.coordinates:
        coords_str = f"LAT {report.coordinates.get('latitude', 'N/A')}° / LON {report.coordinates.get('longitude', 'N/A')}°"

    score_val = report.severity_assessment.get("severity_score") or report.severity_assessment.get("composite_score", 0)

    suggested_actions_html = "".join(
        f"<li class='flex items-start gap-2 text-on-surface-variant text-sm'><span class='text-secondary-container'>▸</span> {act}</li>"
        for act in report.recommendations.suggested_actions
    )

    trend_html = ""
    if report.trend_summary:
        trend_html = f"""
        <div class="mt-4 p-4 rounded bg-surface-container-low border border-outline-variant/30">
            <div class="text-xs font-mono uppercase tracking-wider text-primary-fixed-dim">Historical Trend Trajectory</div>
            <div class="text-sm font-semibold text-on-surface mt-1">{report.trend_summary.get('summary_text', 'Tracking enabled')}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html class="dark" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>{report.title} - MarineGuard AI</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet"/>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
    tailwind.config = {{
        darkMode: "class",
        theme: {{
            extend: {{
                colors: {{
                    "background": "#051426",
                    "surface": "#051426",
                    "surface-container": "#122033",
                    "surface-container-low": "#0e1c2e",
                    "surface-container-high": "#1d2b3e",
                    "primary": "#e0fdff",
                    "primary-container": "#00f2fe",
                    "primary-fixed-dim": "#00dce6",
                    "secondary-container": "#36ffc4",
                    "on-surface": "#d5e3fd",
                    "on-surface-variant": "#b9cacb",
                    "outline-variant": "#3a494b",
                    "error": "#ffb4ab",
                    "error-container": "#93000a"
                }},
                fontFamily: {{
                    sans: ["Plus Jakarta Sans", "sans-serif"],
                    display: ["Space Grotesk", "sans-serif"],
                    mono: ["JetBrains Mono", "monospace"]
                }}
            }}
        }}
    }};
    </script>
    <style>
        @media print {{
            body {{ background-color: #051426 !important; -webkit-print-color-adjust: exact; }}
            .no-print {{ display: none !important; }}
        }}
    </style>
</head>
<body class="bg-background font-sans text-on-surface min-h-screen p-6 md:p-12">
    <div class="max-w-4xl mx-auto space-y-6">
        <!-- Action Bar (Print / Export) -->
        <div class="no-print flex items-center justify-between pb-4 border-b border-outline-variant/40">
            <div class="text-xs font-mono text-on-surface-variant">DOCUMENT CLASSIFICATION: ENVIRONMENTAL INTELLIGENCE</div>
            <button onclick="window.print()" class="px-4 py-2 bg-primary-container text-[#002022] font-semibold text-xs rounded hover:bg-primary transition shadow-md flex items-center gap-2">
                <span>🖶</span> Print / Save PDF
            </button>
        </div>

        <!-- Header -->
        <header class="p-6 rounded-lg bg-surface-container border border-outline-variant/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
                <div class="flex items-center gap-2 mb-1">
                    <span class="font-display text-primary text-xl font-bold tracking-wider">MARINEGUARD AI</span>
                    <span class="font-mono text-xs px-2 py-0.5 rounded bg-surface-container-high text-primary-fixed-dim border border-primary-fixed-dim/30">SDG-14 REPORT</span>
                </div>
                <h1 class="text-2xl font-bold font-display text-on-surface">{report.title}</h1>
                <p class="text-sm text-on-surface-variant font-mono mt-1">Location: {report.location} {('· ' + coords_str) if coords_str else ''}</p>
            </div>
            <div class="text-right">
                <div class="text-xs font-mono text-on-surface-variant">REPORT ID: {report.report_id}</div>
                <div class="text-xs font-mono text-on-surface-variant">GENERATED: {report.generated_at[:19].replace('T', ' ')} UTC</div>
            </div>
        </header>

        <!-- KPI Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="p-4 rounded-lg bg-surface-container border border-outline-variant/30">
                <div class="text-xs font-mono text-on-surface-variant uppercase">Estimated Score</div>
                <div class="text-3xl font-display font-bold text-primary mt-1">{score_val}<span class="text-sm font-mono text-on-surface-variant font-normal"> / 100</span></div>
            </div>
            <div class="p-4 rounded-lg bg-surface-container border border-outline-variant/30">
                <div class="text-xs font-mono text-on-surface-variant uppercase">Severity Level</div>
                <div class="mt-2 inline-block px-2.5 py-1 rounded text-xs font-mono font-bold border {badge_cls}">{sev_level.upper()}</div>
            </div>
            <div class="p-4 rounded-lg bg-surface-container border border-outline-variant/30">
                <div class="text-xs font-mono text-on-surface-variant uppercase">Total Detections</div>
                <div class="text-3xl font-display font-bold text-secondary-container mt-1">{report.metrics.get('total_detections', 0)}</div>
            </div>
            <div class="p-4 rounded-lg bg-surface-container border border-outline-variant/30">
                <div class="text-xs font-mono text-on-surface-variant uppercase">Avg Confidence</div>
                <div class="text-3xl font-display font-bold text-on-surface mt-1">{round(report.metrics.get('average_confidence', 0.0) * 100, 1)}<span class="text-sm font-mono text-on-surface-variant font-normal">%</span></div>
            </div>
        </div>

        <!-- Trend Summary if present -->
        {trend_html}

        <!-- Recommendations Section -->
        <div class="p-6 rounded-lg bg-surface-container border border-outline-variant/30 space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-display font-bold text-primary">Recommended Operational Actions</h2>
                <span class="text-xs font-mono px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant border border-outline-variant/40">Priority: {report.recommendations.urgency}</span>
            </div>
            <div class="p-3.5 rounded bg-surface-container-low border border-outline-variant/30">
                <div class="text-xs font-mono text-primary-fixed-dim uppercase tracking-wider mb-1">Primary Directive</div>
                <p class="text-sm font-medium text-on-surface">{report.recommendations.primary_action}</p>
            </div>
            <div>
                <div class="text-xs font-mono text-on-surface-variant uppercase tracking-wider mb-2">Suggested Field Protocols</div>
                <ul class="space-y-2">
                    {suggested_actions_html}
                </ul>
            </div>
        </div>

        <!-- Methodology & Disclaimer -->
        <footer class="p-4 rounded-lg bg-surface-container-lowest border border-outline-variant/30 text-xs font-mono text-on-surface-variant/80 space-y-2">
            <div class="text-primary-fixed-dim font-bold">METHODOLOGY & SCIENTIFIC BOUNDARIES</div>
            <p>{report.disclaimer}</p>
            <div class="text-[10px] text-outline pt-2 border-t border-outline-variant/20">
                Marine Pollution Image Analyzer · Autonomous Environmental Intelligence Engine · PS-3Y-14 Track
            </div>
        </footer>
    </div>
</body>
</html>"""
