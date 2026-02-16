"""Initial tables for case-service: patients, cases.

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
        "patients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(255), unique=True, nullable=True),
        sa.Column("demographics", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_patients_external_id", "patients", ["external_id"])

    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="CREATED"),
        sa.Column("tags", sa.JSON, server_default="[]"),
        sa.Column("metadata", sa.JSON, server_default="{}"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_cases_patient_id", "cases", ["patient_id"])
    op.create_index("idx_cases_status", "cases", ["status"])


def downgrade() -> None:
    op.drop_table("cases")
    op.drop_table("patients")
