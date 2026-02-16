"""Initial tables for image-service: images.

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
        "images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("format", sa.String(10), nullable=False, server_default="png"),
        sa.Column("storage_uri", sa.String(1024), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("stain", sa.String(100), nullable=True),
        sa.Column("magnification", sa.String(50), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("uploaded_by", sa.String(255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_images_case_id", "images", ["case_id"])


def downgrade() -> None:
    op.drop_table("images")
