"""Inference API routes — v2 (ABMIL + Choquet + SHAP Decomposition)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models import MLJobDB, ResultBundleDB, XAIArtifactDB
from app.tasks import process_image_task

router = APIRouter(prefix="/api/v1", tags=["Inference"])


@router.post("/images/{image_id}:process", status_code=status.HTTP_202_ACCEPTED)
async def process_image(
    image_id: str,
    body: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Start async inference job (DERCAS UC-IMG-02)."""
    body = body or {}
    case_id = body.get("case_id", "unknown")
    thresholds = body.get("thresholds")

    job_id = str(uuid4())
    job = MLJobDB(
        id=job_id,
        case_id=case_id,
        image_id=image_id,
        job_type="IMAGE_INFERENCE",
        status="PENDING",
    )
    db.add(job)
    await db.commit()

    # Dispatch Celery task
    process_image_task.delay(job_id, image_id, case_id, thresholds)

    return {
        "job_id": job_id,
        "image_id": image_id,
        "status": "PENDING",
        "message": "Inference job queued",
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Poll job status."""
    job = await db.get(MLJobDB, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "image_id": job.image_id,
        "status": job.status,
        "progress": job.progress,
        "result_bundle_id": job.result_bundle_id,
        "error_code": job.error_code,
        "error_detail": job.error_detail,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("/images/{image_id}/results/latest")
async def get_latest_results(image_id: str, db: AsyncSession = Depends(get_db)):
    """Get latest ResultBundle for an image."""
    stmt = (
        select(ResultBundleDB)
        .where(ResultBundleDB.image_id == image_id)
        .options(
            selectinload(ResultBundleDB.pattern_results),
            selectinload(ResultBundleDB.genetic_results),
            selectinload(ResultBundleDB.xai_artifacts),
            selectinload(ResultBundleDB.morphologic_profile),
        )
        .order_by(ResultBundleDB.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="No results found")
    return _bundle_dict(bundle)


@router.get("/results/{result_bundle_id}")
async def get_result_bundle(result_bundle_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ResultBundleDB)
        .where(ResultBundleDB.id == result_bundle_id)
        .options(
            selectinload(ResultBundleDB.pattern_results),
            selectinload(ResultBundleDB.genetic_results),
            selectinload(ResultBundleDB.xai_artifacts),
            selectinload(ResultBundleDB.morphologic_profile),
        )
    )
    result = await db.execute(stmt)
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Result bundle not found")
    return _bundle_dict(bundle)


@router.get("/results/{result_bundle_id}/artifacts")
async def get_artifacts(result_bundle_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(XAIArtifactDB).where(XAIArtifactDB.result_bundle_id == result_bundle_id)
    result = await db.execute(stmt)
    return [
        {
            "artifact_id": a.id,
            "artifact_type": a.artifact_type,
            "gene": a.gene,
            "uri": a.uri,
            "hash": a.hash,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]


@router.get("/checkpoints/status")
async def get_checkpoint_status():
    """Return which v2 checkpoints are loaded per gene."""
    try:
        from app.ml.checkpoints.loader import CheckpointLoader
        loader = CheckpointLoader(settings.v2_checkpoint_dir, "cpu")
        return loader.get_checkpoint_status()
    except Exception as e:
        return {"error": str(e), "checkpoint_dir": settings.v2_checkpoint_dir}


def _bundle_dict(b: ResultBundleDB) -> dict:
    mp = b.morphologic_profile
    return {
        "result_bundle_id": b.id,
        "case_id": b.case_id,
        "image_id": b.image_id,
        "job_id": b.job_id,
        "model_profile": b.model_profile,
        "model_version": b.model_version,
        "pipeline_version": getattr(b, "pipeline_version", None) or "1.0.0",
        "use_choquet": getattr(b, "use_choquet", None),
        "thresholds": b.thresholds,
        "pattern_composition": b.pattern_composition,
        "predominant_pattern": b.predominant_pattern,
        "evidence_source": b.evidence_source,
        "intended_use": b.intended_use,
        "pattern_results": [
            {
                "pattern": pr.pattern,
                "score": pr.score,
                "percentage": pr.percentage,
                "is_conclusive": pr.is_conclusive,
                "overlay_uri": pr.overlay_uri,
            }
            for pr in (b.pattern_results or [])
        ],
        "genetic_results": [
            {
                "mutation": gr.mutation,
                "score": gr.score,
                "status": gr.status,
                "confidence_label": getattr(gr, "confidence_label", None),
                "auroc_threshold": getattr(gr, "auroc_threshold", None),
                "prediction_method": getattr(gr, "prediction_method", None),
                "disclaimer": getattr(gr, "disclaimer", None),
                "shap_decomposition": {
                    "embedding_contribution_pct": getattr(gr, "shap_embedding_pct", None),
                    "pattern_contribution_pct": getattr(gr, "shap_pattern_pct", None),
                    "top_pattern_dims": getattr(gr, "shap_top_patterns", None),
                } if getattr(gr, "shap_embedding_pct", None) is not None else None,
                "choquet_shapley": {
                    "shapley_values": getattr(gr, "choquet_shapley_values", None),
                    "interaction_indices": getattr(gr, "choquet_interaction_indices", None),
                } if getattr(gr, "choquet_shapley_values", None) is not None else None,
                "evidence_source": gr.evidence_source,
                "intended_use": gr.intended_use,
            }
            for gr in (b.genetic_results or [])
        ],
        "morphologic_profile": {
            "n_tiles_total": mp.n_tiles_total,
            "pct_lepidic": mp.pct_lepidic,
            "pct_acinar": mp.pct_acinar,
            "pct_papillary": mp.pct_papillary,
            "pct_micropapillary": mp.pct_micropapillary,
            "pct_solid": mp.pct_solid,
            "pct_mucinous": mp.pct_mucinous,
        } if mp else None,
        "attention_overlay_uri": getattr(b, "attention_overlay_uri", None),
        "xai_artifacts": [
            {"artifact_id": a.id, "type": a.artifact_type, "gene": a.gene, "uri": a.uri}
            for a in (b.xai_artifacts or [])
        ],
        "disclaimers": [
            "This is a research tool, NOT a clinical diagnostic device.",
            "v2 mutation predictions use Pattern-Informed ABMIL + Fuzzy Choquet MIL (thesis Artifacts 2 & 3).",
            "Inconclusive genes (AUROC < 0.70) require molecular testing for confirmation.",
            "Always confirm with standard molecular testing.",
        ],
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }
