from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.analysis import DetectionOut, ReportResponse
from app.services.analysis_lookup import get_analysis_or_404
from app.services.report_service import build_report

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.get("/reports/{analysis_id}", response_model=ReportResponse)
def get_report(analysis_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    analysis = get_analysis_or_404(analysis_id, db)

    detections = [
        DetectionOut(
            class_name=d.class_name,
            confidence=d.confidence,
            bbox=[d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
            area_ratio=d.area_ratio,
        )
        for d in analysis.detections
    ]
    return build_report(analysis, detections)
