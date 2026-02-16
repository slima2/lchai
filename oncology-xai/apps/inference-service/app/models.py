"""SQLAlchemy models for inference results."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oncology_common.database import Base


class MLJobDB(Base):
    __tablename__ = "ml_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str | None] = mapped_column(String(36), index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), default="IMAGE_INFERENCE")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    result_bundle_id: Mapped[str | None] = mapped_column(String(36))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ResultBundleDB(Base):
    __tablename__ = "result_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("ml_jobs.id"), nullable=False)
    model_profile: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    pattern_composition: Mapped[dict] = mapped_column(JSON, default=dict)
    predominant_pattern: Mapped[str | None] = mapped_column(String(50))
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    evidence_source: Mapped[str] = mapped_column(String(50), default="THESIS_INTERNAL")
    intended_use: Mapped[str] = mapped_column(String(200), default="research / decision support (non-diagnostic)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    pattern_results: Mapped[list["PatternResultDB"]] = relationship(back_populates="result_bundle", cascade="all, delete-orphan")
    genetic_results: Mapped[list["GeneticResultDB"]] = relationship(back_populates="result_bundle", cascade="all, delete-orphan")
    xai_artifacts: Mapped[list["XAIArtifactDB"]] = relationship(back_populates="result_bundle", cascade="all, delete-orphan")
    morphologic_profile: Mapped["MorphologicProfileDB | None"] = relationship(back_populates="result_bundle", uselist=False, cascade="all, delete-orphan")


class PatternResultDB(Base):
    __tablename__ = "pattern_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_bundle_id: Mapped[str] = mapped_column(String(36), ForeignKey("result_bundles.id"), nullable=False, index=True)
    pattern: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    is_conclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    overlay_uri: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    result_bundle: Mapped["ResultBundleDB"] = relationship(back_populates="pattern_results")


class GeneticResultDB(Base):
    __tablename__ = "genetic_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_bundle_id: Mapped[str] = mapped_column(String(36), ForeignKey("result_bundles.id"), nullable=False, index=True)
    mutation: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(50), default="THESIS_INTERNAL")
    intended_use: Mapped[str] = mapped_column(String(200), default="research / decision support (non-diagnostic)")
    evidence_uri: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    result_bundle: Mapped["ResultBundleDB"] = relationship(back_populates="genetic_results")


class XAIArtifactDB(Base):
    __tablename__ = "xai_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_bundle_id: Mapped[str] = mapped_column(String(36), ForeignKey("result_bundles.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    gene: Mapped[str | None] = mapped_column(String(20))
    uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    result_bundle: Mapped["ResultBundleDB"] = relationship(back_populates="xai_artifacts")


class MorphologicProfileDB(Base):
    __tablename__ = "morphologic_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_bundle_id: Mapped[str] = mapped_column(String(36), ForeignKey("result_bundles.id"), unique=True, nullable=False)
    n_tiles_total: Mapped[int] = mapped_column(Integer, default=0)
    pct_lepidic: Mapped[float] = mapped_column(Float, default=0.0)
    pct_acinar: Mapped[float] = mapped_column(Float, default=0.0)
    pct_papillary: Mapped[float] = mapped_column(Float, default=0.0)
    pct_micropapillary: Mapped[float] = mapped_column(Float, default=0.0)
    pct_solid: Mapped[float] = mapped_column(Float, default=0.0)
    pct_mucinous: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    result_bundle: Mapped["ResultBundleDB"] = relationship(back_populates="morphologic_profile")
