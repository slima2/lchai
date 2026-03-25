"""Celery tasks for inference."""

from __future__ import annotations

import io
import hashlib
import json
import logging
from datetime import datetime
from uuid import uuid4

from app.celery_app import celery
from app.config import settings
from app.database import get_sync_db
from app.models import (
    MLJobDB, ResultBundleDB, PatternResultDB,
    GeneticResultDB, XAIArtifactDB, MorphologicProfileDB,
)
from app.roi_inference_ctranspath_fuzzyarcloss_v3 import (
    InferenceConfig, InferenceResult, run_inference,
)

from oncology_common.storage import StorageClient
from event_contracts import EventEnvelope, EventPublisher

logger = logging.getLogger(__name__)


def _storage() -> StorageClient:
    return StorageClient(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )


@celery.task(bind=True, name="inference.process_image", max_retries=2)
def process_image_task(self, job_id: str, image_id: str, case_id: str, thresholds: dict | None = None):
    """Run full inference pipeline for an image."""
    db = get_sync_db()
    storage = _storage()

    def _update_progress(pct: float, stage: str = ""):
        try:
            j = db.query(MLJobDB).filter_by(id=job_id).first()
            if j:
                j.progress = round(pct, 2)
                if stage:
                    j.error_detail = stage
                db.commit()
        except Exception:
            pass

    try:
        job = db.query(MLJobDB).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = "RUNNING"
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        job.error_detail = "Downloading image..."
        db.commit()

        _update_progress(0.05, "Downloading image...")

        # Download image from MinIO and get format for decode
        from sqlalchemy import text
        row = db.execute(
            text("SELECT storage_uri, format FROM images WHERE id = :id"),
            {"id": image_id},
        ).fetchone()

        image_format = (row[1] or "").strip().lower() if row and row[1] else None
        if row and row[0]:
            uri = row[0]
            key = uri.replace(f"s3://{settings.s3_bucket}/", "")
            if not image_format and "." in key:
                image_format = key.rsplit(".", 1)[-1].lower()
            image_bytes = storage.download_bytes(key)
        else:
            # If no image in DB yet (e.g. mock), use placeholder
            from PIL import Image as PILImage
            img = PILImage.new("RGB", (448, 448), (200, 200, 200))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        # Build config (v2) — auto-detect GPU
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Inference device: %s (CUDA available: %s)", device, torch.cuda.is_available())
        if device == "cuda":
            logger.info("GPU: %s, VRAM: %.1f GB", torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory / 1e9)

        # Resolve original slide name for TCGA detection (via patient external_id)
        slide_name_row = db.execute(
            text("""SELECT p.external_id FROM images i
                    JOIN cases c ON i.case_id = c.id
                    JOIN patients p ON c.patient_id = p.id
                    WHERE i.id = :id"""),
            {"id": image_id},
        ).fetchone()
        slide_name = slide_name_row[0] if slide_name_row and slide_name_row[0] else ""
        original_filename = slide_name or (key if row and row[0] else f"image:{image_id}")
        logger.info("Slide origin: name=%s, is_tcga=%s", slide_name[:60] if slide_name else "unknown", "TCGA" in original_filename.upper())

        thr = thresholds or {}
        config = InferenceConfig(
            image_uri=original_filename,
            image_format=image_format,
            device=device,
            model_backend=settings.model_backend,
            ctranspath_checkpoint=settings.ctranspath_checkpoint,
            fuzzyarc_checkpoint=settings.fuzzyarc_checkpoint,
            mutation_model_dir=settings.mutation_model_dir,
            v2_checkpoint_dir=settings.v2_checkpoint_dir,
            use_choquet=settings.use_choquet,
            top_k_tiles=settings.v2_top_k_tiles,
            max_tiles_wsi=settings.v2_max_tiles_wsi,
            genes=settings.genes_list,
            pattern_threshold=thr.get("pattern", settings.pattern_threshold),
            mutation_threshold=thr.get("mutation", settings.mutation_threshold),
            shap_enabled=settings.shap_enabled,
            shap_decomposition_enabled=settings.shap_decomposition_enabled,
        )

        _update_progress(0.10, "Running v2 inference pipeline...")

        result = run_inference(image_bytes, config, progress_callback=_update_progress)

        _update_progress(0.85, "Saving artifacts to MinIO...")

        # Persist artifacts to MinIO
        rb_id = str(uuid4())
        prefix = f"results/{case_id}/{rb_id}"

        # Upload clean thumbnail (original image without overlays)
        if result.thumbnail_bytes:
            thumb_key = f"{prefix}/thumbnail.png"
            storage.upload_bytes(thumb_key, result.thumbnail_bytes, "image/png")

        overlay_key = f"{prefix}/roi_overlay_combined.png"
        storage.upload_bytes(overlay_key, result.overlay_combined_bytes, "image/png")

        comp_json = json.dumps(result.pattern_percentages).encode()
        storage.upload_bytes(f"{prefix}/pattern_composition.json", comp_json, "application/json")

        if result.embedding is not None:
            import numpy as np
            emb_buf = io.BytesIO()
            np.savez_compressed(emb_buf, embedding=result.embedding)
            storage.upload_bytes(f"{prefix}/embedding.npz", emb_buf.getvalue(), "application/octet-stream")

        metrics_json = json.dumps(result.metrics).encode()
        storage.upload_bytes(f"{prefix}/metrics.json", metrics_json, "application/json")

        # Upload attention overlay if available
        attention_overlay_uri = None
        if result.attention_overlay_bytes:
            attn_key = f"{prefix}/attention_overlay.png"
            storage.upload_bytes(attn_key, result.attention_overlay_bytes, "image/png")
            attention_overlay_uri = f"s3://{settings.s3_bucket}/{attn_key}"
            attn_art = XAIArtifactDB(
                result_bundle_id=rb_id,
                artifact_type="attention_overlay",
                gene=None,
                uri=attention_overlay_uri,
                hash=hashlib.sha256(result.attention_overlay_bytes).hexdigest(),
            )
            db.add(attn_art)

        # Upload combined overlay (patterns + attention contours)
        if result.combined_overlay_bytes:
            comb_key = f"{prefix}/combined_overlay.png"
            storage.upload_bytes(comb_key, result.combined_overlay_bytes, "image/png")
            comb_art = XAIArtifactDB(
                result_bundle_id=rb_id,
                artifact_type="combined_overlay",
                gene=None,
                uri=f"s3://{settings.s3_bucket}/{comb_key}",
                hash=hashlib.sha256(result.combined_overlay_bytes).hexdigest(),
            )
            db.add(comb_art)

        # Upload pattern region map (JSON) for interactive hover
        if result.pattern_region_map:
            region_json = json.dumps(result.pattern_region_map).encode()
            region_key = f"{prefix}/pattern_region_map.json"
            storage.upload_bytes(region_key, region_json, "application/json")
            region_art = XAIArtifactDB(
                result_bundle_id=rb_id,
                artifact_type="pattern_region_map",
                gene=None,
                uri=f"s3://{settings.s3_bucket}/{region_key}",
                hash=hashlib.sha256(region_json).hexdigest(),
            )
            db.add(region_art)

        # Persist ResultBundle to DB (v2)
        bundle = ResultBundleDB(
            id=rb_id,
            case_id=case_id,
            image_id=image_id,
            job_id=job_id,
            model_profile="ctranspath_fuzzyarcloss_v2_abmil_choquet",
            model_version="v2.0.0-mock" if config.model_backend == "mock" else "v2.0.0",
            pipeline_version="2.0.0",
            use_choquet=config.use_choquet,
            attention_overlay_uri=attention_overlay_uri,
            thresholds={"pattern": config.pattern_threshold, "mutation": config.mutation_threshold},
            pattern_composition=result.pattern_percentages,
            predominant_pattern=result.predominant_pattern,
            evidence_source="THESIS_INTERNAL",
            intended_use="research / decision support (non-diagnostic)",
        )
        db.add(bundle)
        db.flush()

        # Pattern results
        for p in result.pattern_scores:
            pr = PatternResultDB(
                result_bundle_id=rb_id,
                pattern=p,
                score=result.pattern_scores[p],
                percentage=result.pattern_percentages.get(p, 0.0),
                is_conclusive=result.is_conclusive.get(p, False),
                overlay_uri=f"s3://{settings.s3_bucket}/{overlay_key}",
            )
            db.add(pr)

        # Build lookup dicts for v2 SHAP and Choquet data
        shap_by_gene = {d.gene: d for d in result.shap_decompositions}
        choquet_by_gene = {c.gene: c for c in result.choquet_shapley}
        ablation_by_gene = {
            a.gene: {"p_proposed": a.p_proposed, "p_emb_only": a.p_emb_only,
                      "p_pat_only": a.p_pat_only, "delta_patterns": a.delta_patterns,
                      "proposed_auroc": a.proposed_auroc,
                      "baseline2_auroc": a.baseline2_auroc,
                      "baseline3_auroc": a.baseline3_auroc,
                      "choquet_auroc": a.choquet_auroc,
                      "auroc_delta": a.auroc_delta}
            for a in result.ablation_results
        }
        permutation_by_gene = {
            p.gene: {"p_original": p.p_original, "p_permuted_mean": p.p_permuted_mean,
                      "pattern_importance": p.pattern_importance, "importance_pct": p.importance_pct}
            for p in result.permutation_results
        }

        # Genetic results (v2 — with confidence labels + interpretability)
        for entry in result.mutation_report:
            shap_d = shap_by_gene.get(entry.gene)
            choquet_d = choquet_by_gene.get(entry.gene)
            gr = GeneticResultDB(
                result_bundle_id=rb_id,
                mutation=entry.gene,
                score=entry.probability,
                status=result.mutation_status.get(entry.gene, "INCONCLUSIVE"),
                confidence_label=entry.label,
                auroc_threshold=entry.auroc_threshold,
                prediction_method=entry.method,
                disclaimer=entry.disclaimer,
                shap_embedding_pct=shap_d.embedding_contribution_pct if shap_d else None,
                shap_pattern_pct=shap_d.pattern_contribution_pct if shap_d else None,
                shap_top_patterns=shap_d.top_pattern_dims if shap_d else None,
                choquet_shapley_values=choquet_d.shapley_values if choquet_d else None,
                choquet_interaction_indices=choquet_d.interaction_indices if choquet_d else None,
                ablation_data=ablation_by_gene.get(entry.gene),
                permutation_data=permutation_by_gene.get(entry.gene),
            )
            db.add(gr)

        # Fallback: persist any genes from mutation_scores not already in mutation_report
        reported_genes = {e.gene for e in result.mutation_report}
        for gene in result.mutation_scores:
            if gene not in reported_genes:
                gr = GeneticResultDB(
                    result_bundle_id=rb_id,
                    mutation=gene,
                    score=result.mutation_scores[gene],
                    status=result.mutation_status.get(gene, "INCONCLUSIVE"),
                )
                db.add(gr)

        # Morphologic profile
        mp = MorphologicProfileDB(
            result_bundle_id=rb_id,
            n_tiles_total=result.n_tiles,
            pct_lepidic=result.morphologic_profile.get("pct_lepidic", 0.0),
            pct_acinar=result.morphologic_profile.get("pct_acinar", 0.0),
            pct_papillary=result.morphologic_profile.get("pct_papillary", 0.0),
            pct_micropapillary=result.morphologic_profile.get("pct_micropapillary", 0.0),
            pct_solid=result.morphologic_profile.get("pct_solid", 0.0),
            pct_mucinous=result.morphologic_profile.get("pct_mucinous", 0.0),
        )
        db.add(mp)

        # ROI overlay artifact
        if result.thumbnail_bytes:
            thumb_art = XAIArtifactDB(
                result_bundle_id=rb_id,
                artifact_type="thumbnail",
                gene=None,
                uri=f"s3://{settings.s3_bucket}/{thumb_key}",
                hash=hashlib.sha256(result.thumbnail_bytes).hexdigest(),
            )
            db.add(thumb_art)

        overlay_art = XAIArtifactDB(
            result_bundle_id=rb_id,
            artifact_type="roi_overlay",
            gene=None,
            uri=f"s3://{settings.s3_bucket}/{overlay_key}",
            hash=hashlib.sha256(result.overlay_combined_bytes).hexdigest(),
        )
        db.add(overlay_art)

        # SHAP artifacts
        for name, data in result.shap_artifacts.items():
            shap_key = f"{prefix}/xai/{name}"
            storage.upload_bytes(shap_key, data, "image/png")
            gene = name.split("_")[1] if "_" in name else None
            art = XAIArtifactDB(
                result_bundle_id=rb_id,
                artifact_type="shap",
                gene=gene,
                uri=f"s3://{settings.s3_bucket}/{shap_key}",
                hash=hashlib.sha256(data).hexdigest(),
            )
            db.add(art)

        # Update job → COMPLETED
        job.status = "COMPLETED"
        job.result_bundle_id = rb_id
        job.ended_at = datetime.utcnow()
        job.progress = 1.0
        db.commit()

        # Emit event
        try:
            pub = EventPublisher(settings.rabbitmq_url)
            pub.publish(EventEnvelope(
                event_type="inference.completed",
                producer="inference-service",
                case_id=case_id,
                payload={
                    "job_id": job_id,
                    "result_bundle_id": rb_id,
                    "image_id": image_id,
                    "entity_type": "result_bundle",
                    "entity_id": rb_id,
                    "action": "inference.completed",
                },
            ))
        except Exception:
            logger.exception("Failed to publish inference.completed event")

        return {"job_id": job_id, "result_bundle_id": rb_id, "status": "COMPLETED"}

    except Exception as e:
        logger.exception("Inference task failed for job %s", job_id)
        db.rollback()
        job = db.query(MLJobDB).filter_by(id=job_id).first()
        if job:
            job.status = "FAILED"
            job.error_code = type(e).__name__
            job.error_detail = str(e)
            job.ended_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()


import io  # noqa: E402 — needed by task body
