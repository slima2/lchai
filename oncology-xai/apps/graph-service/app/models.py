"""SQLAlchemy models for graph snapshots."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oncology_common.database import Base


class CaseGraphSnapshotDB(Base):
    __tablename__ = "case_graph_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    triplestore_graph_iri: Mapped[str | None] = mapped_column(String(500))
    nodes_json: Mapped[dict] = mapped_column(JSON, default=list)
    edges_json: Mapped[dict] = mapped_column(JSON, default=list)
    ontology_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    layout_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
