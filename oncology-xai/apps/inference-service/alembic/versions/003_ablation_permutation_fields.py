"""Add ablation + permutation fields to genetic_results.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("genetic_results", sa.Column("ablation_data", sa.JSON(), nullable=True))
    op.add_column("genetic_results", sa.Column("permutation_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("genetic_results", "permutation_data")
    op.drop_column("genetic_results", "ablation_data")
