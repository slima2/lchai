"""Initial tables for inference-service.

Tables: ml_jobs, result_bundles, pattern_results, genetic_results,
        xai_artifacts, morphologic_profiles.

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
        "ml_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=True),
        sa.Column("image_id", sa.String(36), nullable=False),
        sa.Column("job_type", sa.String(50), server_default="IMAGE_INFERENCE"),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("progress", sa.Float, server_default="0.0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("result_bundle_id", sa.String(36), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ml_jobs_image_id", "ml_jobs", ["image_id"])
    op.create_index("idx_ml_jobs_case_id", "ml_jobs", ["case_id"])
    op.create_index("idx_ml_jobs_status", "ml_jobs", ["status"])

    op.create_table(
        "result_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("image_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("ml_jobs.id"), nullable=False),
        sa.Column("model_profile", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("thresholds", sa.JSON, server_default="{}"),
        sa.Column("pattern_composition", sa.JSON, server_default="{}"),
        sa.Column("predominant_pattern", sa.String(50), nullable=True),
        sa.Column("summary_json", sa.JSON, nullable=True),
        sa.Column("evidence_source", sa.String(50), server_default="THESIS_INTERNAL", nullable=False),
        sa.Column("intended_use", sa.String(200), server_default="research / decision support (non-diagnostic)", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_result_bundles_case_id", "result_bundles", ["case_id"])
    op.create_index("idx_result_bundles_image_id", "result_bundles", ["image_id"])

    op.create_table(
        "pattern_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("result_bundle_id", sa.String(36), sa.ForeignKey("result_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pattern", sa.String(50), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("percentage", sa.Float, server_default="0.0"),
        sa.Column("is_conclusive", sa.Boolean, server_default="true"),
        sa.Column("overlay_uri", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_pattern_results_bundle", "pattern_results", ["result_bundle_id"])

    op.create_table(
        "genetic_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("result_bundle_id", sa.String(36), sa.ForeignKey("result_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mutation", sa.String(20), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evidence_source", sa.String(50), server_default="THESIS_INTERNAL"),
        sa.Column("intended_use", sa.String(200), server_default="research / decision support (non-diagnostic)"),
        sa.Column("evidence_uri", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_genetic_results_bundle", "genetic_results", ["result_bundle_id"])

    op.create_table(
        "xai_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("result_bundle_id", sa.String(36), sa.ForeignKey("result_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(100), nullable=False),
        sa.Column("gene", sa.String(20), nullable=True),
        sa.Column("uri", sa.String(1024), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_xai_artifacts_bundle", "xai_artifacts", ["result_bundle_id"])

    op.create_table(
        "morphologic_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("result_bundle_id", sa.String(36), sa.ForeignKey("result_bundles.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("n_tiles_total", sa.Integer, server_default="0"),
        sa.Column("pct_lepidic", sa.Float, server_default="0.0"),
        sa.Column("pct_acinar", sa.Float, server_default="0.0"),
        sa.Column("pct_papillary", sa.Float, server_default="0.0"),
        sa.Column("pct_micropapillary", sa.Float, server_default="0.0"),
        sa.Column("pct_solid", sa.Float, server_default="0.0"),
        sa.Column("pct_mucinous", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("morphologic_profiles")
    op.drop_table("xai_artifacts")
    op.drop_table("genetic_results")
    op.drop_table("pattern_results")
    op.drop_table("result_bundles")
    op.drop_table("ml_jobs")
