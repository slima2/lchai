"""Persist signed per-pattern SHAP values + directions.

Adds two JSON columns to ``genetic_results`` so the UI can show
the *direction* of each pattern's contribution (positive / negative
toward mutated), not only its absolute magnitude.

  - ``shap_pattern_signed``     : {pattern_name: signed_shap_value}
  - ``shap_pattern_directions`` : {pattern_name: "positive"|"negative"|"neutral"}

Both are nullable so legacy rows remain valid.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "genetic_results",
        sa.Column("shap_pattern_signed", sa.JSON(), nullable=True),
    )
    op.add_column(
        "genetic_results",
        sa.Column("shap_pattern_directions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("genetic_results", "shap_pattern_directions")
    op.drop_column("genetic_results", "shap_pattern_signed")
