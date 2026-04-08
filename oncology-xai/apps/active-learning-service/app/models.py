"""SQLAlchemy models for active learning."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class PatternCorrectionDB(Base):
    __tablename__ = "pattern_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_bundle_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tile_index: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_x: Mapped[float] = mapped_column(Float, nullable=False)
    tile_y: Mapped[float] = mapped_column(Float, nullable=False)
    original_pattern: Mapped[str] = mapped_column(String(50), nullable=False)
    corrected_pattern: Mapped[str] = mapped_column(String(50), nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(100), default="pathologist")
    model_version_before: Mapped[str | None] = mapped_column(String(100))
    model_version_after: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelVersionDB(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_tag: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    pth_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    parent_version: Mapped[str | None] = mapped_column(String(100))
    corrections_count: Mapped[int] = mapped_column(Integer, default=0)
    slide_id: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
