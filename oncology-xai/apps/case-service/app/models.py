"""SQLAlchemy models for patients and cases."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oncology_common.database import Base
from oncology_common.models.entities import CaseStatus


class PatientDB(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    demographics: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=datetime.utcnow)


class CaseDB(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=CaseStatus.CREATED.value, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=datetime.utcnow)
