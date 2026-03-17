"""v2 — ABMIL + Choquet fields for genetic_results and result_bundles.

Revision ID: 002_v2_fields
Revises: 001_initial_tables
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # result_bundles — v2 columns
    op.add_column("result_bundles", sa.Column("pipeline_version", sa.String(20), server_default="2.0.0"))
    op.add_column("result_bundles", sa.Column("use_choquet", sa.Boolean(), server_default="true"))
    op.add_column("result_bundles", sa.Column("attention_overlay_uri", sa.String(1024), nullable=True))

    # genetic_results — v2 confidence + interpretability columns
    op.add_column("genetic_results", sa.Column("confidence_label", sa.String(20), nullable=True))
    op.add_column("genetic_results", sa.Column("auroc_threshold", sa.Float(), nullable=True))
    op.add_column("genetic_results", sa.Column("prediction_method", sa.String(20), nullable=True))
    op.add_column("genetic_results", sa.Column("disclaimer", sa.Text(), nullable=True))
    op.add_column("genetic_results", sa.Column("shap_embedding_pct", sa.Float(), nullable=True))
    op.add_column("genetic_results", sa.Column("shap_pattern_pct", sa.Float(), nullable=True))
    op.add_column("genetic_results", sa.Column("shap_top_patterns", sa.JSON(), nullable=True))
    op.add_column("genetic_results", sa.Column("choquet_shapley_values", sa.JSON(), nullable=True))
    op.add_column("genetic_results", sa.Column("choquet_interaction_indices", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("genetic_results", "choquet_interaction_indices")
    op.drop_column("genetic_results", "choquet_shapley_values")
    op.drop_column("genetic_results", "shap_top_patterns")
    op.drop_column("genetic_results", "shap_pattern_pct")
    op.drop_column("genetic_results", "shap_embedding_pct")
    op.drop_column("genetic_results", "disclaimer")
    op.drop_column("genetic_results", "prediction_method")
    op.drop_column("genetic_results", "auroc_threshold")
    op.drop_column("genetic_results", "confidence_label")
    op.drop_column("result_bundles", "attention_overlay_uri")
    op.drop_column("result_bundles", "use_choquet")
    op.drop_column("result_bundles", "pipeline_version")
