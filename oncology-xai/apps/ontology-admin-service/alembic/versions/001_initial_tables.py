"""Initial tables for ontology-admin-service.

Tables: ontology_versions, ontology_update_proposals, explanation_reports.

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
        "ontology_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("version_tag", sa.String(100), nullable=False),
        sa.Column("source_uri", sa.String(1024), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="false"),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ontology_versions_name", "ontology_versions", ["name"])
    op.create_index("idx_ontology_versions_active", "ontology_versions", ["is_active"])

    op.create_table(
        "ontology_update_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("targets", sa.JSON, server_default="[]"),
        sa.Column("mode", sa.String(20), server_default="offline"),
        sa.Column("status", sa.String(30), server_default="DRAFT", nullable=False),
        sa.Column("diff_report_uri", sa.String(1024), nullable=True),
        sa.Column("impact", sa.JSON, nullable=True),
        sa.Column("reasoner_report_uri", sa.String(1024), nullable=True),
        sa.Column("validation_results", sa.JSON, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_proposals_status", "ontology_update_proposals", ["status"])

    op.create_table(
        "explanation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("result_bundle_id", sa.String(36), nullable=True),
        sa.Column("ehr_id", sa.String(36), nullable=True),
        sa.Column("graph_snapshot_id", sa.String(36), nullable=True),
        sa.Column("report_uri", sa.String(1024), nullable=False),
        sa.Column("format", sa.String(20), server_default="html"),
        sa.Column("guardrails_passed", sa.Boolean, server_default="true"),
        sa.Column("guardrails_violations", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_explanation_reports_case_id", "explanation_reports", ["case_id"])


def downgrade() -> None:
    op.drop_table("explanation_reports")
    op.drop_table("ontology_update_proposals")
    op.drop_table("ontology_versions")
