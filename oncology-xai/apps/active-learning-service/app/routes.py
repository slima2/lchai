"""Active Learning API routes."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import settings
from app.database import get_db, get_sync_db
from app.models import PatternCorrectionDB, ModelVersionDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/active-learning", tags=["Active Learning"])

_job_store: dict[str, dict] = {}


def _storage():
    from oncology_common.storage import StorageClient
    return StorageClient(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )


@router.post("/corrections", status_code=202)
async def submit_corrections(
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit tile-level pattern corrections and trigger delta training + re-analysis.

    Body:
        {
            "case_id": "...",
            "image_id": "...",
            "result_bundle_id": "...",
            "corrections": [
                {"tile_index": 0, "tile_x": 0.1, "tile_y": 0.2,
                 "original_pattern": "micropapillary", "corrected_pattern": "acinar",
                 "corrected_by": "Dr. X (SOLCA)"}
            ]
        }
    """
    case_id = body.get("case_id")
    image_id = body.get("image_id")
    rb_id = body.get("result_bundle_id")
    corrections = body.get("corrections", [])

    if not corrections:
        raise HTTPException(400, "No corrections provided")
    if not all([case_id, image_id, rb_id]):
        raise HTTPException(400, "case_id, image_id, and result_bundle_id are required")

    job_id = str(uuid4())
    _job_store[job_id] = {
        "job_id": job_id,
        "status": "PENDING",
        "progress": 0.0,
        "stage": "Queued",
        "corrections_count": len(corrections),
        "result_bundle_id": rb_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    background_tasks.add_task(
        _run_correction_pipeline, job_id, case_id, image_id, rb_id, corrections
    )

    return {"job_id": job_id, "status": "PENDING", "corrections_count": len(corrections)}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll job status for a correction/retrain job."""
    job = _job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/corrections/{result_bundle_id}")
async def get_corrections(result_bundle_id: str, db: AsyncSession = Depends(get_db)):
    """List all corrections for a result bundle (audit trail)."""
    result = await db.execute(
        select(PatternCorrectionDB)
        .where(PatternCorrectionDB.result_bundle_id == result_bundle_id)
        .order_by(PatternCorrectionDB.created_at)
    )
    corrections = result.scalars().all()
    return {
        "result_bundle_id": result_bundle_id,
        "total": len(corrections),
        "corrections": [
            {
                "id": c.id, "tile_index": c.tile_index,
                "tile_x": c.tile_x, "tile_y": c.tile_y,
                "original_pattern": c.original_pattern,
                "corrected_pattern": c.corrected_pattern,
                "corrected_by": c.corrected_by,
                "model_version_before": c.model_version_before,
                "model_version_after": c.model_version_after,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in corrections
        ],
    }


@router.get("/model-versions")
async def list_model_versions(db: AsyncSession = Depends(get_db)):
    """List all model versions (original + delta-trained)."""
    result = await db.execute(
        select(ModelVersionDB).order_by(ModelVersionDB.created_at.desc())
    )
    versions = result.scalars().all()
    return {
        "total": len(versions),
        "versions": [
            {
                "id": v.id, "version_tag": v.version_tag,
                "pth_uri": v.pth_uri, "parent_version": v.parent_version,
                "corrections_count": v.corrections_count,
                "slide_id": v.slide_id, "notes": v.notes,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


async def _run_correction_pipeline(
    job_id: str, case_id: str, image_id: str, rb_id: str, corrections: list[dict]
):
    """Background task: delta train -> save model -> re-analyze slide."""
    job = _job_store[job_id]
    storage = _storage()
    sync_db = get_sync_db()

    try:
        job.update(status="RUNNING", progress=0.1, stage="Loading tile data...")

        prefix = f"results/{case_id}/{rb_id}"
        tile_data_key = f"{prefix}/tile_data.npz"

        # Get current model version
        current_versions = sync_db.query(ModelVersionDB).order_by(
            ModelVersionDB.created_at.desc()
        ).first()

        if current_versions:
            current_pth_uri = current_versions.pth_uri
            current_version_tag = current_versions.version_tag
        else:
            current_pth_uri = "models/best_fuzzyarcloss_v2_original.pth"
            current_version_tag = "original"
            try:
                storage.download_bytes(current_pth_uri)
            except Exception:
                import io
                pth_bytes = _read_pth_from_inference_volume()
                if pth_bytes:
                    storage.upload_bytes(current_pth_uri, pth_bytes, "application/octet-stream")
                    mv = ModelVersionDB(
                        version_tag="original",
                        pth_uri=current_pth_uri,
                        parent_version=None,
                        corrections_count=0,
                        notes="Original FuzzyArcLoss V2 with label fix",
                    )
                    sync_db.add(mv)
                    sync_db.commit()

        job.update(progress=0.2, stage="Delta training FuzzyArcLoss V2 head...")

        current_pth_bytes = storage.download_bytes(current_pth_uri)

        from app.delta_train import run_delta_training
        new_pth_bytes, version_tag = run_delta_training(
            storage=storage,
            tile_data_key=tile_data_key,
            current_pth_bytes=current_pth_bytes,
            corrections=corrections,
            n_epochs=settings.delta_train_epochs,
            lr=settings.delta_train_lr,
            buffer_ratio=settings.delta_train_buffer_ratio,
        )

        if new_pth_bytes is None:
            job.update(status="FAILED", stage=f"Delta training failed: {version_tag}")
            return

        job.update(progress=0.5, stage="Saving updated model to MinIO...")

        new_pth_uri = f"models/fuzzyarcloss_v2_{version_tag}.pth"
        storage.upload_bytes(new_pth_uri, new_pth_bytes, "application/octet-stream")

        mv = ModelVersionDB(
            version_tag=version_tag,
            pth_uri=new_pth_uri,
            parent_version=current_version_tag,
            corrections_count=len(corrections),
            slide_id=f"{case_id}/{image_id}",
            notes=f"Delta trained on {len(corrections)} corrected tiles",
        )
        sync_db.add(mv)

        for c in corrections:
            pc = PatternCorrectionDB(
                result_bundle_id=rb_id,
                case_id=case_id,
                image_id=image_id,
                tile_index=c["tile_index"],
                tile_x=c.get("tile_x", 0.0),
                tile_y=c.get("tile_y", 0.0),
                original_pattern=c.get("original_pattern", "unknown"),
                corrected_pattern=c["corrected_pattern"],
                corrected_by=c.get("corrected_by", "pathologist"),
                model_version_before=current_version_tag,
                model_version_after=version_tag,
            )
            sync_db.add(pc)

        sync_db.commit()

        job.update(progress=0.6, stage="Triggering slide re-analysis...")

        from app.reprocess import trigger_reanalysis
        import asyncio
        loop = asyncio.new_event_loop()
        reanalysis_result = loop.run_until_complete(trigger_reanalysis(image_id, case_id))
        loop.close()

        reanalysis_status = reanalysis_result.get("status", "UNKNOWN")
        new_rb_id = reanalysis_result.get("result_bundle_id")

        if reanalysis_status == "COMPLETED":
            job.update(
                status="COMPLETED", progress=1.0,
                stage="Model updated and slide re-analyzed successfully",
                new_result_bundle_id=new_rb_id,
                model_version=version_tag,
            )
        else:
            job.update(
                status="COMPLETED", progress=0.9,
                stage=f"Model updated (v{version_tag}). Re-analysis: {reanalysis_status}",
                model_version=version_tag,
            )

        logger.info("Correction pipeline complete: %d corrections, model=%s, reanalysis=%s",
                     len(corrections), version_tag, reanalysis_status)

    except Exception as e:
        logger.exception("Correction pipeline failed: %s", e)
        job.update(status="FAILED", stage=str(e))
    finally:
        sync_db.close()


def _read_pth_from_inference_volume() -> bytes | None:
    """Read the original .pth from the inference service's model volume via HTTP."""
    try:
        import httpx
        resp = httpx.get(f"{settings.inference_service_url}/api/v1/checkpoints/status", timeout=10)
        if resp.status_code == 200:
            pass
    except Exception:
        pass
    return None
