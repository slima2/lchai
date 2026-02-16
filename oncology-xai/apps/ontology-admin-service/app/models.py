"""SQLAlchemy models for ontology versions and proposals."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oncology_common.database import Base


class OntologyVersionDB(Base):
    __tablename__ = "ontology_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class OntologyUpdateProposalDB(Base):
    __tablename__ = "ontology_update_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    targets: Mapped[dict] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(20), default="offline")
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    diff_report_uri: Mapped[str | None] = mapped_column(String(1024))
    impact: Mapped[dict | None] = mapped_column(JSON)
    reasoner_report_uri: Mapped[str | None] = mapped_column(String(1024))
    validation_results: Mapped[dict | None] = mapped_column(JSON)
    created_by: Mapped[str | None] = mapped_column(String(255))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KGSnapshotDB(Base):
    """Knowledge Graph version snapshot."""
    __tablename__ = "kg_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    nodes_count: Mapped[int] = mapped_column(default=0)
    edges_count: Mapped[int] = mapped_column(default=0)
    snapshot_uri: Mapped[str | None] = mapped_column(String(1024))  # s3://...jsonld
    format: Mapped[str] = mapped_column(String(20), default="jsonld")
    sources: Mapped[dict | None] = mapped_column(JSON)  # list of sources used
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class KGChangelogEntryDB(Base):
    """Individual change in a KG snapshot."""
    __tablename__ = "kg_changelog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # ADDED, REMOVED, UPDATED
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)  # node, edge
    entity_id: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DeepSearchJobDB(Base):
    """DeepSearch pipeline execution."""
    __tablename__ = "deep_search_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    source_text: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), default="text")  # text, paper, kb_export
    extracted_relations: Mapped[dict | None] = mapped_column(JSON)
    linked_entities: Mapped[dict | None] = mapped_column(JSON)
    validation_result: Mapped[dict | None] = mapped_column(JSON)
    snapshot_id: Mapped[str | None] = mapped_column(String(36))
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscoveredRelationDB(Base):
    """Relations discovered by DeepSearch batch from literature."""
    __tablename__ = "discovered_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    predicate: Mapped[str] = mapped_column(String(100), nullable=False)
    object: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_iri: Mapped[str | None] = mapped_column(String(500))
    object_iri: Mapped[str | None] = mapped_column(String(500))
    subject_type: Mapped[str | None] = mapped_column(String(30))
    object_type: Mapped[str | None] = mapped_column(String(30))
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    paper_source: Mapped[str | None] = mapped_column(String(50))
    paper_id: Mapped[str | None] = mapped_column(String(200))
    paper_title: Mapped[str | None] = mapped_column(Text)
    paper_url: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplanationReportDB(Base):
    __tablename__ = "explanation_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    result_bundle_id: Mapped[str | None] = mapped_column(String(36))
    ehr_id: Mapped[str | None] = mapped_column(String(36))
    graph_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    report_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="html")
    guardrails_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    guardrails_violations: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
