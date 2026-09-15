"""ORM models for a single analyze request: the uploaded image, the
detections found in it, and the overall analysis/severity/location summary.

Matches the frozen API contract in docs/api-contract.md — `Analysis.id` is an
autoincrement integer internally, exposed publicly as "ANL-0001" style via
`Analysis.public_id`.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    analyses: Mapped[list[Analysis]] = relationship(back_populates="image")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), nullable=False)

    # Internal bookkeeping (not part of the frozen API response shape).
    mode: Mapped[str] = mapped_column(String, nullable=False)  # "mock" | "real"
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional location, per the contract's request fields.
    location_name: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation_date: Mapped[str | None] = mapped_column(String, nullable=True)

    # Summary, per the contract's response "summary" object.
    dominant_category: Mapped[str] = mapped_column(String, nullable=False)
    total_detections: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # Low/Moderate/High/Critical
    severity_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    image: Mapped[Image] = relationship(back_populates="analyses")
    detections: Mapped[list[Detection]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )

    @property
    def public_id(self) -> str:
        return f"ANL-{self.id:04d}"


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), nullable=False)
    class_name: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float, nullable=False)
    area_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    analysis: Mapped[Analysis] = relationship(back_populates="detections")
