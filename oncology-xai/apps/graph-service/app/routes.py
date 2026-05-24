"""Graph Service routes (DERCAS 9.6)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.explain import generate_explanation
from app.models import CaseGraphSnapshotDB
from app.sparql import get_case_subgraph

router = APIRouter(prefix="/api/v1", tags=["Graph"])


async def _fetch_case_label(db: AsyncSession, case_id: str) -> str | None:
    """Resolve a human-friendly label for the case node: the patient's external_id when available."""
    stmt = text(
        "SELECT p.external_id FROM patients p JOIN cases c ON c.patient_id = p.id WHERE c.id = :cid"
    )
    row = (await db.execute(stmt, {"cid": case_id})).fetchone()
    return row[0] if row and row[0] else None


async def _fetch_case_results(db: AsyncSession, case_id: str) -> tuple[list[dict], list[dict]]:
    """Fetch pattern_results and genetic_results for the latest result_bundle of a case."""
    # Find latest result bundle for this case
    rb_stmt = text(
        "SELECT id FROM result_bundles WHERE case_id = :cid ORDER BY created_at DESC LIMIT 1"
    )
    rb_row = (await db.execute(rb_stmt, {"cid": case_id})).first()
    if not rb_row:
        return [], []

    rb_id = rb_row[0]

    # Pattern results
    pat_stmt = text(
        "SELECT pattern, score, percentage, is_conclusive FROM pattern_results WHERE result_bundle_id = :rid"
    )
    pat_rows = (await db.execute(pat_stmt, {"rid": rb_id})).fetchall()
    patterns = [
        {"pattern": r[0], "score": float(r[1]), "percentage": float(r[2]), "is_conclusive": bool(r[3])}
        for r in pat_rows
        if (r[0] or "").lower() != "mucinous"
    ]

    # Genetic results
    gen_stmt = text(
        "SELECT mutation, score, status FROM genetic_results WHERE result_bundle_id = :rid"
    )
    gen_rows = (await db.execute(gen_stmt, {"rid": rb_id})).fetchall()
    genetics = [
        {"mutation": r[0], "score": float(r[1]), "status": r[2]}
        for r in gen_rows
    ]

    return patterns, genetics


async def _fetch_discovered_relations(db: AsyncSession) -> list[dict]:
    """Fetch active discovered relations from batch DeepSearch jobs."""
    stmt = text(
        "SELECT subject, predicate, object, subject_iri, object_iri, "
        "subject_type, object_type, evidence_quote, paper_source, paper_id, paper_title "
        "FROM discovered_relations WHERE is_active = true "
        "ORDER BY created_at DESC LIMIT 200"
    )
    try:
        rows = (await db.execute(stmt)).fetchall()
    except Exception:
        await db.rollback()
        return []
    return [
        {
            "subject": r[0], "predicate": r[1], "object": r[2],
            "subject_iri": r[3], "object_iri": r[4],
            "subject_type": r[5], "object_type": r[6],
            "evidence_quote": r[7], "paper_source": r[8],
            "paper_id": r[9], "paper_title": r[10],
        }
        for r in rows
    ]


@router.get("/graph/gene-associations")
async def get_gene_associations(db: AsyncSession = Depends(get_db)):
    """Return pattern-gene and gene-treatment associations from the KG.

    Combines curated edges with DeepSearch-discovered relations so that
    all LLM prompts use the latest KG state as their ground truth.
    """
    from app.ontology_loader import (
        CURATED_EDGES, CURATED_NODES,
        GENE_NAME_TO_IRI, PATTERN_NAME_TO_IRI,
    )

    iri_to_name: dict[str, str] = {}
    for n_id, n_data in CURATED_NODES.items():
        iri_to_name[n_data.get("iri", n_id)] = n_data.get("label", n_id)

    gene_iri_to_name = {v: k for k, v in GENE_NAME_TO_IRI.items()}
    pattern_iri_to_name = {v: k for k, v in PATTERN_NAME_TO_IRI.items()}

    pattern_gene: list[dict] = []
    gene_treatment: list[dict] = []

    for e in CURATED_EDGES:
        if e["label"] == "associatedWithMutation":
            pat = pattern_iri_to_name.get(e["s"], iri_to_name.get(e["s"], e["s"]))
            gene = gene_iri_to_name.get(e["t"], iri_to_name.get(e["t"], e["t"]))
            pattern_gene.append({
                "pattern": pat, "gene": gene,
                "provenance": e.get("prov", "curated"), "source": "curated",
            })
        elif e["label"] == "treatedWith":
            gene = gene_iri_to_name.get(e["s"], iri_to_name.get(e["s"], e["s"]))
            drug = iri_to_name.get(e["t"], e["t"])
            gene_treatment.append({
                "gene": gene, "treatment": drug,
                "provenance": e.get("prov", "curated"), "source": "curated",
            })

    discovered = await _fetch_discovered_relations(db)
    for rel in discovered:
        if rel.get("predicate") == "associatedWithMutation":
            pattern_gene.append({
                "pattern": rel.get("subject_label", ""),
                "gene": rel.get("object_label", ""),
                "provenance": rel.get("provenance", "DeepSearch"),
                "source": "deepsearch",
            })
        elif rel.get("predicate") == "treatedWith":
            gene_treatment.append({
                "gene": rel.get("subject_label", ""),
                "treatment": rel.get("object_label", ""),
                "provenance": rel.get("provenance", "DeepSearch"),
                "source": "deepsearch",
            })

    assoc_by_gene: dict[str, dict] = {}
    for pg in pattern_gene:
        g = pg["gene"]
        if g not in assoc_by_gene:
            assoc_by_gene[g] = {"gene": g, "patterns": [], "treatments": []}
        assoc_by_gene[g]["patterns"].append({
            "pattern": pg["pattern"],
            "provenance": pg["provenance"],
            "source": pg["source"],
        })
    for gt in gene_treatment:
        g = gt["gene"]
        if g not in assoc_by_gene:
            assoc_by_gene[g] = {"gene": g, "patterns": [], "treatments": []}
        assoc_by_gene[g]["treatments"].append({
            "treatment": gt["treatment"],
            "provenance": gt["provenance"],
            "source": gt["source"],
        })

    return {
        "associations": list(assoc_by_gene.values()),
        "total_pattern_gene_edges": len(pattern_gene),
        "total_gene_treatment_edges": len(gene_treatment),
        "sources": ["curated", "deepsearch"],
    }


@router.get("/cases/{case_id}/graph")
async def get_graph(
    case_id: str,
    depth: int = Query(2, ge=1, le=5),
    include_inferred: bool = Query(True, alias="includeInferred"),
    db: AsyncSession = Depends(get_db),
):
    """Get graph for a case (from latest snapshot or live SPARQL)."""
    # Try latest snapshot
    stmt = (
        select(CaseGraphSnapshotDB)
        .where(CaseGraphSnapshotDB.case_id == case_id)
        .order_by(CaseGraphSnapshotDB.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if snapshot:
        nodes = snapshot.nodes_json or []
        edges = snapshot.edges_json or []
        if not include_inferred:
            edges = [e for e in edges if e.get("type") != "inferred"]
        ov = snapshot.ontology_versions or {}
        return {
            "graph_snapshot_id": snapshot.id,
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges,
            "ontology_versions": ov,
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "graph_source": ov.get("graph_source"),
            "graph_source_message": ov.get("graph_source_message"),
        }

    # Live query
    graph = await get_case_subgraph(settings.fuseki_url, settings.fuseki_dataset, case_id, depth)
    if not include_inferred:
        graph["edges"] = [e for e in graph["edges"] if e.get("type") != "inferred"]
    return {
        "graph_snapshot_id": None,
        "case_id": case_id,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "ontology_versions": {},
        "created_at": None,
        "graph_source": graph.get("source"),
        "graph_source_message": graph.get("source_message"),
    }


@router.post("/cases/{case_id}/graph:rebuild", status_code=201)
async def rebuild_graph(
    case_id: str,
    from_ontology: bool = Query(True, alias="fromOntology"),
    db: AsyncSession = Depends(get_db),
):
    """Rebuild graph snapshot from case results + discovered relations. Dynamic case-specific graph."""
    # Fetch real results for this case
    pattern_results, genetic_results = await _fetch_case_results(db, case_id)

    # Fetch discovered relations from batch DeepSearch
    discovered = await _fetch_discovered_relations(db)

    # Resolve human-friendly label for the case (patient external_id, falls back to short uuid)
    case_label = await _fetch_case_label(db, case_id)

    graph = await get_case_subgraph(
        settings.fuseki_url,
        settings.fuseki_dataset,
        case_id,
        from_ontology=from_ontology,
        pattern_results=pattern_results or None,
        genetic_results=genetic_results or None,
        discovered_relations=discovered or None,
        case_label=case_label,
    )

    ontology_versions = {
        "graph_source": graph.get("source"),
        "graph_source_message": graph.get("source_message"),
    }
    snap = CaseGraphSnapshotDB(
        id=str(uuid4()),
        case_id=case_id,
        triplestore_graph_iri=f"graph:case:{case_id}",
        nodes_json=graph["nodes"],
        edges_json=graph["edges"],
        ontology_versions=ontology_versions,
    )
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return {
        "graph_snapshot_id": snap.id,
        "case_id": case_id,
        "nodes_count": len(graph["nodes"]),
        "edges_count": len(graph["edges"]),
        "graph_source": graph.get("source"),
        "graph_source_message": graph.get("source_message"),
    }


@router.post("/cases/{case_id}/graph/explain")
async def explain_graph(
    case_id: str,
    body: dict | None = None,
    include_inferred: bool = Query(True, alias="includeInferred"),
    db: AsyncSession = Depends(get_db),
):
    """Generate natural language explanation of the case graph via LLM."""
    language = (body or {}).get("language", "en")
    # Fetch graph (same logic as get_graph)
    stmt = (
        select(CaseGraphSnapshotDB)
        .where(CaseGraphSnapshotDB.case_id == case_id)
        .order_by(CaseGraphSnapshotDB.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if snapshot:
        nodes = snapshot.nodes_json or []
        edges = snapshot.edges_json or []
    else:
        graph = await get_case_subgraph(settings.fuseki_url, settings.fuseki_dataset, case_id)
        nodes = graph["nodes"]
        edges = graph["edges"]

    if not include_inferred:
        edges = [e for e in edges if e.get("type") != "inferred"]

    extra_context = (body or {}).get("extra_context", "")
    explanation = await generate_explanation(
        case_id,
        nodes,
        edges,
        openai_api_key=settings.openai_api_key,
        anthropic_api_key=settings.anthropic_api_key,
        llm_provider=settings.llm_provider,
        language=language,
        extra_context=extra_context,
    )
    return {"case_id": case_id, "explanation": explanation}


@router.get("/graphs/{graph_snapshot_id}")
async def get_snapshot(graph_snapshot_id: str, db: AsyncSession = Depends(get_db)):
    snap = await db.get(CaseGraphSnapshotDB, graph_snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Graph snapshot not found")
    return {
        "graph_snapshot_id": snap.id,
        "case_id": snap.case_id,
        "nodes": snap.nodes_json,
        "edges": snap.edges_json,
        "ontology_versions": snap.ontology_versions,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
    }
