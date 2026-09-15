"""Shared helper for resolving a public "ANL-0001" style id to an Analysis
row, used by both the analyze and reports routes.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.analysis import Analysis


def get_analysis_or_404(analysis_id: str, db: Session) -> Analysis:
    numeric_id = None
    if analysis_id.startswith("ANL-"):
        try:
            numeric_id = int(analysis_id.removeprefix("ANL-"))
        except ValueError:
            numeric_id = None

    analysis = db.get(Analysis, numeric_id) if numeric_id is not None else None
    if analysis is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Analysis not found"}
        )
    return analysis
