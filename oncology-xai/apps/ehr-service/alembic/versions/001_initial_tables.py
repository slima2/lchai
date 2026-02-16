"""Initial tables for ehr-service: ehr_documents, ehr_entities, ehr_mappings.

Revision ID: 001
Revises:
Create Date: 2026-02-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ehr_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("source", sa.String(50), server_default="paste"),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("content_uri", sa.String(1024), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ehr_documents_case_id", "ehr_documents", ["case_id"])

    op.create_table(
        "ehr_entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ehr_id", sa.String(36), sa.ForeignKey("ehr_documents.id"), nullable=False),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("start", sa.Integer, nullable=False),
        sa.Column("end", sa.Integer, nullable=False),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ehr_entities_ehr_id", "ehr_entities", ["ehr_id"])

    op.create_table(
        "ehr_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("ehr_entities.id"), nullable=False),
        sa.Column("ontology", sa.String(20), nullable=False),
        sa.Column("iri", sa.String(500), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("mapping_method", sa.String(100), server_default="keyword_lookup"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ehr_mappings_entity_id", "ehr_mappings", ["entity_id"])


def downgrade() -> None:
    op.drop_table("ehr_mappings")
    op.drop_table("ehr_entities")
    op.drop_table("ehr_documents")
