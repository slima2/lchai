"""Initial tables for graph-service: case_graph_snapshots.

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
        "case_graph_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("triplestore_graph_iri", sa.String(500), nullable=True),
        sa.Column("nodes_json", sa.JSON, server_default="[]"),
        sa.Column("edges_json", sa.JSON, server_default="[]"),
        sa.Column("ontology_versions", sa.JSON, server_default="{}"),
        sa.Column("layout_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_graph_snapshots_case_id", "case_graph_snapshots", ["case_id"])


def downgrade() -> None:
    op.drop_table("case_graph_snapshots")
