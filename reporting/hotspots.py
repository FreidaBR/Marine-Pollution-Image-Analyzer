"""
Location Intelligence & Hotspot Detection Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Aggregates observations across coastal locations, computes spatial clusters,
ranks high-risk zones, and identifies priority environmental hotspots.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
from collections import defaultdict
from reporting.schemas import (
    SeverityLevel,
    LocationCluster,
    AnalysisResult,
    SurveyResult,
)
from reporting.severity import score_to_severity_level


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def aggregate_location_intelligence(
    items: List[Any],
    cluster_distance_km: float = 7.5,
    hotspot_score_threshold: int = 60,
) -> List[LocationCluster]:
    """
    Computes location intelligence and identifies pollution hotspots.
    Accepts a list of AnalysisResult, SurveyResult, or dictionary payloads.

    Groups observations by spatial proximity if coordinates are available,
    otherwise groups by location name.
    """
    # 1. Normalize items into records
    records = []
    for item in items:
        if isinstance(item, AnalysisResult):
            loc_name = item.location.name if item.location else "Unknown"
            lat = item.location.latitude if item.location else None
            lon = item.location.longitude if item.location else None
            score = item.summary.severity_score
            dets = item.summary.total_detections
        elif isinstance(item, SurveyResult):
            loc_name = item.location_summary.get("name", "Unknown") if item.location_summary else item.survey_name
            lat = item.location_summary.get("latitude") if item.location_summary else None
            lon = item.location_summary.get("longitude") if item.location_summary else None
            score = item.average_score
            dets = item.total_detections
        elif isinstance(item, dict):
            loc = item.get("location") or {}
            loc_name = loc.get("name") if isinstance(loc, dict) else str(item.get("location_name") or "Unknown")
            lat = loc.get("latitude") if isinstance(loc, dict) else item.get("latitude")
            lon = loc.get("longitude") if isinstance(loc, dict) else item.get("longitude")
            summary = item.get("summary") or {}
            score = summary.get("severity_score") or item.get("average_score") or item.get("score", 0)
            dets = summary.get("total_detections") or item.get("total_detections") or item.get("detections", 0)
        else:
            continue

        records.append({
            "name": loc_name or "Unknown Location",
            "lat": float(lat) if lat is not None else None,
            "lon": float(lon) if lon is not None else None,
            "score": int(score),
            "detections": int(dets),
        })

    if not records:
        return []

    # 2. Cluster observations
    # Separate georeferenced records from non-georeferenced
    geo_records = [r for r in records if r["lat"] is not None and r["lon"] is not None]
    non_geo_records = [r for r in records if r["lat"] is None or r["lon"] is None]

    clusters: List[Dict[str, Any]] = []

    # Spatial clustering using Haversine distance
    for r in geo_records:
        assigned = False
        for c in clusters:
            dist = haversine_distance_km(r["lat"], r["lon"], c["center_lat"], c["center_lon"])
            if dist <= cluster_distance_km:
                c["records"].append(r)
                # Recompute centroid
                n = len(c["records"])
                c["center_lat"] = sum(x["lat"] for x in c["records"]) / n
                c["center_lon"] = sum(x["lon"] for x in c["records"]) / n
                assigned = True
                break
        if not assigned:
            clusters.append({
                "name": r["name"],
                "center_lat": r["lat"],
                "center_lon": r["lon"],
                "records": [r],
            })

    # Group non-georeferenced by exact name
    non_geo_groups = defaultdict(list)
    for r in non_geo_records:
        non_geo_groups[r["name"]].append(r)

    for name, group_records in non_geo_groups.items():
        clusters.append({
            "name": name,
            "center_lat": None,
            "center_lon": None,
            "records": group_records,
        })

    # 3. Compute metrics for each cluster
    results: List[LocationCluster] = []
    for c in clusters:
        cluster_records = c["records"]
        count = len(cluster_records)
        total_dets = sum(x["detections"] for x in cluster_records)
        avg_score = int(round(sum(x["score"] for x in cluster_records) / count))
        severity = score_to_severity_level(avg_score)

        # Hotspot logic: score >= hotspot_score_threshold (High/Critical) and total_dets > 0
        is_hotspot = (avg_score >= hotspot_score_threshold and total_dets > 0)

        results.append(
            LocationCluster(
                location=c["name"],
                latitude=round(c["center_lat"], 4) if c["center_lat"] is not None else None,
                longitude=round(c["center_lon"], 4) if c["center_lon"] is not None else None,
                analysis_count=count,
                total_detections=total_dets,
                average_score=avg_score,
                severity=severity,
                is_hotspot=is_hotspot,
            )
        )

    # 4. Rank clusters by risk (average_score desc, then total_detections desc)
    results.sort(key=lambda x: (x.average_score, x.total_detections), reverse=True)
    for rank, cluster in enumerate(results, start=1):
        cluster.risk_rank = rank

    return results
