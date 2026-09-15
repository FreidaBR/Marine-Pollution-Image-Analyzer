from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.models.analysis import Analysis, Detection, Image
from app.schemas.analysis import (
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisResponse,
    AnalysisSummaryOut,
    DetectionOut,
    LocationOut,
)
from app.services.analysis_lookup import get_analysis_or_404
from app.services.inference_service import get_inference_provider
from app.services.severity_service import calculate_severity, dominant_category
from app.services.storage_service import (
    UPLOAD_DIR,
    UploadValidationError,
    save_bytes,
    validate_upload,
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_image(
    image: UploadFile = File(...),
    location_name: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    observation_date: str | None = Form(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalysisResponse:
    try:
        contents = validate_upload(image, settings.max_upload_size_mb)
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    image_row = Image(
        filename=image.filename or "upload",
        stored_path="",  # filled in once the file is written below
        content_type=image.content_type,
    )
    db.add(image_row)
    db.flush()  # assigns image_row.id

    # Flush now (before we know detections/severity) just to obtain
    # analysis.id, so the stored file can use the public "ANL-0001" name
    # from the start — placeholder summary fields are overwritten below.
    analysis = Analysis(
        image_id=image_row.id,
        mode=settings.ai_mode,
        confidence_threshold=settings.ai_confidence_threshold,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        observation_date=observation_date,
        dominant_category="pending",
        total_detections=0,
        severity="Low",
        severity_score=0,
    )
    db.add(analysis)
    db.flush()  # assigns analysis.id

    stored_filename = save_bytes(
        contents, stem=analysis.public_id, original_filename=image.filename or ""
    )
    image_row.stored_path = f"/uploads/{stored_filename}"

    provider = get_inference_provider(settings)
    stored_full_path = str(UPLOAD_DIR / stored_filename)
    try:
        detections = provider.predict(stored_full_path, settings.ai_confidence_threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Model unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Model inference failed") from exc
    severity = calculate_severity(detections)

    analysis.dominant_category = dominant_category(detections)
    analysis.total_detections = len(detections)
    analysis.severity = severity["severity"]
    analysis.severity_score = severity["severity_score"]
    analysis.detections = [
        Detection(
            class_name=d.class_name,
            confidence=d.confidence,
            bbox_x1=d.bbox[0],
            bbox_y1=d.bbox[1],
            bbox_x2=d.bbox[2],
            bbox_y2=d.bbox[3],
            area_ratio=d.area_ratio,
        )
        for d in detections
    ]

    db.commit()
    db.refresh(analysis)

    return _to_response(analysis, detections)


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> AnalysisListResponse:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    total = db.query(Analysis).count()
    rows = db.query(Analysis).order_by(Analysis.created_at.desc()).offset(offset).limit(limit).all()
    items = [
        AnalysisListItem(
            analysis_id=row.public_id,
            image_url=row.image.stored_path,
            created_at=row.created_at,
            summary=AnalysisSummaryOut(
                dominant_category=row.dominant_category,
                total_detections=row.total_detections,
                severity=row.severity,
                severity_score=row.severity_score,
            ),
        )
        for row in rows
    ]
    return AnalysisListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisResponse:
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
    return _to_response(analysis, detections)


def _to_response(analysis: Analysis, detections: list[DetectionOut]) -> AnalysisResponse:
    location = None
    if analysis.location_name or analysis.latitude is not None:
        location = LocationOut(
            name=analysis.location_name,
            latitude=analysis.latitude,
            longitude=analysis.longitude,
        )

    return AnalysisResponse(
        analysis_id=analysis.public_id,
        image_url=analysis.image.stored_path,
        location=location,
        detections=detections,
        summary=AnalysisSummaryOut(
            dominant_category=analysis.dominant_category,
            total_detections=analysis.total_detections,
            severity=analysis.severity,
            severity_score=analysis.severity_score,
        ),
        report_url=f"/api/v1/reports/{analysis.public_id}",
    )
