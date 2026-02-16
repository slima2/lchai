"""SQLAlchemy models for EHR documents, entities, mappings."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oncology_common.database import Base


class EHRDocumentDB(Base):
    __tablename__ = "ehr_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(50), default="paste")
    content_text: Mapped[str | None] = mapped_column(Text)
    content_uri: Mapped[str | None] = mapped_column(String(1024))
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EHREntityDB(Base):
    __tablename__ = "ehr_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ehr_id: Mapped[str] = mapped_column(String(36), ForeignKey("ehr_documents.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start: Mapped[int] = mapped_column(Integer, nullable=False)
    end: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    section: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EHRMappingDB(Base):
    __tablename__ = "ehr_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("ehr_entities.id"), nullable=False, index=True)
    ontology: Mapped[str] = mapped_column(String(20), nullable=False)
    iri: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    mapping_method: Mapped[str] = mapped_column(String(100), default="keyword_lookup")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
