"""Ontology Admin routes (DERCAS 9.7) + DeepSearch + KG Versioning."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio

from app.config import settings
from app.database import get_db, async_session
from app.deep_search import run_pipeline, extract_relations_llm, entity_link, deduplicate, validate_relations
from app.literature_search import batch_literature_search, DEFAULT_QUERIES
from app.models import (
    OntologyVersionDB, OntologyUpdateProposalDB,
    KGSnapshotDB, KGChangelogEntryDB, DeepSearchJobDB, DiscoveredRelationDB,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Ontology Admin"])


@router.get("/ontologies")
async def list_ontologies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OntologyVersionDB).order_by(OntologyVersionDB.imported_at.desc()))
    return [
        {
            "ontology_version_id": v.id, "name": v.name, "version_tag": v.version_tag,
            "source_uri": v.source_uri, "hash": v.hash, "is_active": v.is_active,
            "imported_at": v.imported_at.isoformat() if v.imported_at else None,
        }
        for v in result.scalars().all()
    ]


@router.post("/ontologies:update-proposal", status_code=status.HTTP_201_CREATED)
async def create_proposal(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    proposal = OntologyUpdateProposalDB(
        id=str(uuid4()),
        targets=body.get("targets", []),
        mode=body.get("mode", "offline"),
        status="DRAFT",
        created_by=body.get("created_by"),
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return _proposal_dict(proposal)


@router.get("/ontologies/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(OntologyUpdateProposalDB, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposal_dict(p)


@router.post("/ontologies/proposals/{proposal_id}:run-validation")
async def run_validation(proposal_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(OntologyUpdateProposalDB, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    p.status = "VALIDATING"
    # Mock validation
    p.validation_results = {"consistency": True, "sparql_tests_passed": 5, "sparql_tests_failed": 0}
    p.status = "VALIDATED"
    await db.commit()
    return _proposal_dict(p)


@router.post("/ontologies/proposals/{proposal_id}:approve-and-publish")
async def approve_and_publish(proposal_id: str, body: dict[str, Any] | None = None, db: AsyncSession = Depends(get_db)):
    p = await db.get(OntologyUpdateProposalDB, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p.status not in ("VALIDATED", "PENDING_APPROVAL"):
        raise HTTPException(status_code=400, detail=f"Cannot publish proposal in status {p.status}")

    p.status = "PUBLISHED"
    p.approved_by = (body or {}).get("approved_by", "admin")
    from datetime import datetime
    p.published_at = datetime.utcnow()
    await db.commit()
    return _proposal_dict(p)


@router.post("/ontologies/proposals/{proposal_id}:rollback")
async def rollback_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(OntologyUpdateProposalDB, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    p.status = "ROLLED_BACK"
    await db.commit()
    return _proposal_dict(p)


def _proposal_dict(p: OntologyUpdateProposalDB) -> dict:
    return {
        "proposal_id": p.id, "targets": p.targets, "mode": p.mode, "status": p.status,
        "diff_report_uri": p.diff_report_uri, "impact": p.impact,
        "reasoner_report_uri": p.reasoner_report_uri, "validation_results": p.validation_results,
        "created_by": p.created_by, "approved_by": p.approved_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
    }


# ──────────────────────────────────────────────────────────────────────
# DeepSearch Pipeline
# ──────────────────────────────────────────────────────────────────────

@router.post("/deep-search", status_code=status.HTTP_201_CREATED)
async def run_deep_search(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Run DeepSearch pipeline: ingest → extract → link → dedup → validate."""
    text = body.get("text", "")
    source_type = body.get("source_type", "text")
    if not text:
        raise HTTPException(400, "text is required")

    job = DeepSearchJobDB(
        id=str(uuid4()),
        source_text=text[:5000],
        source_type=source_type,
        status="RUNNING",
    )
    db.add(job)
    await db.flush()

    try:
        result = await run_pipeline(
            text, source_type,
            llm_provider=settings.llm_provider,
            openai_api_key=settings.openai_api_key,
            anthropic_api_key=settings.anthropic_api_key,
        )
        job.extracted_relations = result.get("valid_relations", [])
        job.linked_entities = {
            "raw_count": result["raw_count"],
            "linked_count": result["linked_count"],
            "deduped_count": result["deduped_count"],
            "valid_count": result["valid_count"],
            "invalid_count": result["invalid_count"],
        }
        job.validation_result = {
            "valid": result["valid_relations"],
            "invalid": result["invalid_relations"],
        }
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        job.status = "FAILED"
        job.error = str(exc)[:500]

    await db.commit()
    await db.refresh(job)
    return _job_dict(job)


@router.get("/deep-search/jobs")
async def list_deep_search_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeepSearchJobDB).order_by(DeepSearchJobDB.created_at.desc()).limit(20)
    )
    return [_job_dict(j) for j in result.scalars().all()]


@router.get("/deep-search/jobs/{job_id}")
async def get_deep_search_job(job_id: str, db: AsyncSession = Depends(get_db)):
    j = await db.get(DeepSearchJobDB, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return _job_dict(j)


def _job_dict(j: DeepSearchJobDB) -> dict:
    return {
        "job_id": j.id, "status": j.status, "source_type": j.source_type,
        "extracted_relations": j.extracted_relations,
        "linked_entities": j.linked_entities,
        "validation_result": j.validation_result,
        "error": j.error,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
    }


# ──────────────────────────────────────────────────────────────────────
# KG Versioning
# ──────────────────────────────────────────────────────────────────────

@router.post("/kg/snapshots", status_code=status.HTTP_201_CREATED)
async def create_kg_snapshot(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Create a new KG version snapshot from validated DeepSearch results."""
    version_tag = body.get("version_tag", datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M"))
    description = body.get("description", "")
    relations = body.get("relations", [])

    snap = KGSnapshotDB(
        id=str(uuid4()),
        version_tag=version_tag,
        description=description,
        nodes_count=len({r.get("subject_iri") for r in relations} | {r.get("object_iri") for r in relations}),
        edges_count=len(relations),
        sources=body.get("sources", ["DeepSearch"]),
        format="jsonld",
        created_by=body.get("created_by"),
    )
    db.add(snap)

    # Create changelog entries
    for rel in relations:
        entry = KGChangelogEntryDB(
            id=str(uuid4()),
            snapshot_id=snap.id,
            action="ADDED",
            entity_type="edge",
            entity_id=f"{rel.get('subject', '?')} → {rel.get('predicate', '?')} → {rel.get('object', '?')}",
            detail=json.dumps(rel, default=str),
            provenance=rel.get("evidence_quote", ""),
        )
        db.add(entry)

    await db.commit()
    await db.refresh(snap)
    return _snapshot_dict(snap)


@router.get("/kg/snapshots")
async def list_kg_snapshots(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KGSnapshotDB).order_by(KGSnapshotDB.created_at.desc()).limit(50)
    )
    return [_snapshot_dict(s) for s in result.scalars().all()]


@router.get("/kg/snapshots/{snapshot_id}")
async def get_kg_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(KGSnapshotDB, snapshot_id)
    if not s:
        raise HTTPException(404, "Snapshot not found")
    return _snapshot_dict(s)


@router.get("/kg/snapshots/{snapshot_id}/changelog")
async def get_kg_changelog(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KGChangelogEntryDB)
        .where(KGChangelogEntryDB.snapshot_id == snapshot_id)
        .order_by(KGChangelogEntryDB.created_at.desc())
    )
    return [
        {
            "id": e.id, "action": e.action, "entity_type": e.entity_type,
            "entity_id": e.entity_id, "detail": e.detail, "provenance": e.provenance,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in result.scalars().all()
    ]


def _snapshot_dict(s: KGSnapshotDB) -> dict:
    return {
        "snapshot_id": s.id, "version_tag": s.version_tag, "description": s.description,
        "nodes_count": s.nodes_count, "edges_count": s.edges_count,
        "snapshot_uri": s.snapshot_uri, "format": s.format, "sources": s.sources,
        "created_by": s.created_by,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ──────────────────────────────────────────────────────────────────────
# Batch Literature DeepSearch (long-running background job)
# ──────────────────────────────────────────────────────────────────────

@router.post("/deep-search/batch", status_code=status.HTTP_202_ACCEPTED)
async def start_batch_deep_search(body: dict[str, Any] | None = None, db: AsyncSession = Depends(get_db)):
    """Launch batch literature search across PubMed, arXiv, Semantic Scholar.

    Runs in background: searches → extracts relations via LLM → links → validates → persists.
    """
    body = body or {}
    queries = body.get("queries") or DEFAULT_QUERIES
    sources = body.get("sources") or ["pubmed", "semantic_scholar", "arxiv"]

    job = DeepSearchJobDB(
        id=str(uuid4()),
        source_type="batch_literature",
        status="RUNNING",
        source_text=json.dumps({"queries": queries[:3], "sources": sources, "total_queries": len(queries)}),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Fire and forget background task
    asyncio.create_task(_run_batch_job(job.id, queries, sources))

    return {
        "job_id": job.id,
        "status": "RUNNING",
        "message": f"Batch search started: {len(queries)} queries across {', '.join(sources)}. This may take several minutes.",
        "queries_count": len(queries),
        "sources": sources,
    }


async def _run_batch_job(job_id: str, queries: list[str], sources: list[str]) -> None:
    """Background: search literature, extract & validate relations, persist."""
    async with async_session() as db:
        job = await db.get(DeepSearchJobDB, job_id)
        if not job:
            return

        try:
            # Step 1: Batch literature search
            papers = await batch_literature_search(queries, sources, max_per_source=3)
            logger.info("Batch job %s: found %d papers", job_id[:8], len(papers))

            all_valid: list[dict] = []
            all_invalid: list[dict] = []
            papers_processed = 0

            # Step 2-5: For each paper, extract → link → dedup → validate
            for paper in papers:
                abstract = paper.get("abstract", "")
                if not abstract or len(abstract) < 50:
                    continue

                try:
                    raw = await extract_relations_llm(
                        abstract,
                        llm_provider=settings.llm_provider,
                        openai_api_key=settings.openai_api_key,
                        anthropic_api_key=settings.anthropic_api_key,
                    )
                    linked = entity_link(raw)
                    deduped = deduplicate(linked)
                    validation = validate_relations(deduped)

                    # Attach paper metadata to each relation
                    for rel in validation["valid"]:
                        rel["paper_source"] = paper.get("source", "")
                        rel["paper_id"] = paper.get("id", "")
                        rel["paper_title"] = paper.get("title", "")
                        rel["paper_url"] = paper.get("url", "")
                    all_valid.extend(validation["valid"])
                    all_invalid.extend(validation["invalid"])
                    papers_processed += 1
                except Exception as e:
                    logger.warning("Extraction failed for paper %s: %s", paper.get("id", "?")[:20], e)

            # Deduplicate across all papers
            seen: set[tuple] = set()
            unique_valid: list[dict] = []
            for rel in all_valid:
                key = (rel.get("subject_iri"), rel.get("predicate"), rel.get("object_iri"))
                if key not in seen and all(key):
                    seen.add(key)
                    unique_valid.append(rel)

            # Persist discovered relations
            for rel in unique_valid:
                dr = DiscoveredRelationDB(
                    id=str(uuid4()),
                    job_id=job_id,
                    subject=rel.get("subject", ""),
                    predicate=rel.get("predicate", ""),
                    object=rel.get("object", ""),
                    subject_iri=rel.get("subject_iri"),
                    object_iri=rel.get("object_iri"),
                    subject_type=rel.get("subject_type"),
                    object_type=rel.get("object_type"),
                    evidence_quote=rel.get("evidence_quote", "")[:500],
                    paper_source=rel.get("paper_source", ""),
                    paper_id=rel.get("paper_id", ""),
                    paper_title=rel.get("paper_title", "")[:300],
                    paper_url=rel.get("paper_url", ""),
                    confidence="high" if rel.get("linked") else "medium",
                )
                db.add(dr)

            # Update job
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            job.linked_entities = {
                "papers_found": len(papers),
                "papers_processed": papers_processed,
                "raw_relations": len(all_valid) + len(all_invalid),
                "valid_unique": len(unique_valid),
                "invalid_count": len(all_invalid),
            }
            job.extracted_relations = unique_valid[:100]  # store first 100
            job.validation_result = {
                "valid_count": len(unique_valid),
                "invalid_count": len(all_invalid),
                "sources": list({r.get("paper_source", "") for r in unique_valid}),
            }
            await db.commit()
            logger.info(
                "Batch job %s COMPLETED: %d papers → %d unique valid relations",
                job_id[:8], papers_processed, len(unique_valid),
            )

        except Exception as exc:
            job.status = "FAILED"
            job.error = str(exc)[:500]
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Batch job %s FAILED: %s", job_id[:8], exc)


@router.get("/deep-search/discovered")
async def list_discovered_relations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all discovered relations from batch searches."""
    result = await db.execute(
        select(DiscoveredRelationDB)
        .where(DiscoveredRelationDB.is_active == True)
        .order_by(DiscoveredRelationDB.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": r.id, "subject": r.subject, "predicate": r.predicate, "object": r.object,
            "subject_iri": r.subject_iri, "object_iri": r.object_iri,
            "subject_type": r.subject_type, "object_type": r.object_type,
            "evidence_quote": r.evidence_quote,
            "paper_source": r.paper_source, "paper_id": r.paper_id,
            "paper_title": r.paper_title, "paper_url": r.paper_url,
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in result.scalars().all()
    ]
