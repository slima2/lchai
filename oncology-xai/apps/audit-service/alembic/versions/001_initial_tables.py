"""Initial tables for audit-service: audit_events.

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
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(64), unique=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("case_id", sa.String(36), nullable=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="SUCCESS"),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_audit_events_event_id", "audit_events", ["event_id"])
    op.create_index("idx_audit_events_type", "audit_events", ["event_type"])
    op.create_index("idx_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index("idx_audit_events_correlation", "audit_events", ["correlation_id"])
    op.create_index("idx_audit_events_case_id", "audit_events", ["case_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
