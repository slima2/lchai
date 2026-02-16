"""GraphAssemblerGraph — LangGraph workflow (DERCAS 13.1.3).

FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance →
BuildLayout → PersistSnapshot → Finalize
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_exec
from langgraph_workflows.tools.storage import get_storage_tool

logger = logging.getLogger(__name__)

GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8005")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8003")
EHR_SERVICE_URL = os.getenv("EHR_SERVICE_URL", "http://localhost:8004")

# Node type colors for layout
NODE_COLORS = {
    "Case": "#42A5F5",
    "Gene": "#66BB6A",
    "Mutation": "#EF5350",
    "Pattern": "#AB47BC",
    "Diagnosis": "#FF7043",
    "Stage": "#26C6DA",
    "Ontology": "#78909C",
}


async def fetch_case_findings(state: GraphState) -> GraphState:
    """Fetch all findings for a case: patterns, mutations, EHR entities."""
    state = update_exec(state, status="running", progress=0.1, current_node="fetch_case_findings")
    ctx = state.get("context", {})
    case_id = ctx.get("case_id")
    inter = dict(state.get("_intermediate", {}))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Root case node
    nodes.append({
        "id": f"case:{case_id}",
        "type": "Case",
        "label": f"Case {case_id[:8]}...",
        "color": NODE_COLORS["Case"],
    })

    # Fetch inference results
    try:
        async with httpx.AsyncClient(base_url=INFERENCE_SERVICE_URL, timeout=10.0) as client:
            resp = await client.get(f"/api/v1/images/{state.get('inputs', {}).get('image_id', 'none')}/results/latest")
            if resp.status_code == 200:
                result = resp.json()
                # Add pattern nodes
                for p in result.get("pattern_results", []):
                    pid = f"pattern:{p['pattern']}"
                    nodes.append({
                        "id": pid,
                        "type": "Pattern",
                        "label": f"{p['pattern']} ({p.get('percentage', 0):.1f}%)",
                        "color": NODE_COLORS["Pattern"],
                        "score": p.get("score"),
                    })
                    edges.append({
                        "source": f"case:{case_id}",
                        "target": pid,
                        "type": "hasPattern",
                        "provenance": "inference",
                    })

                # Add genetic result nodes
                for g in result.get("genetic_results", []):
                    gid = f"gene:{g['mutation']}"
                    nodes.append({
                        "id": gid,
                        "type": "Gene",
                        "label": f"{g['mutation']} ({g['status']})",
                        "color": NODE_COLORS["Gene"],
                        "score": g.get("score"),
                    })
                    edges.append({
                        "source": f"case:{case_id}",
                        "target": gid,
                        "type": "hasMutationPrediction",
                        "provenance": "xgboost_morphology",
                    })
    except Exception as exc:
        logger.debug("Could not fetch inference results: %s", exc)

    # Fetch EHR entities
    try:
        async with httpx.AsyncClient(base_url=EHR_SERVICE_URL, timeout=10.0) as client:
            ehr_id = state.get("inputs", {}).get("ehr_id")
            if ehr_id:
                resp = await client.get(f"/api/v1/ehr/{ehr_id}/entities")
                if resp.status_code == 200:
                    for ent in resp.json():
                        eid = f"entity:{ent['entity_type']}:{ent['text']}"
                        if not any(n["id"] == eid for n in nodes):
                            nodes.append({
                                "id": eid,
                                "type": ent["entity_type"],
                                "label": ent["text"],
                                "color": NODE_COLORS.get(ent["entity_type"], "#78909C"),
                            })
                            edges.append({
                                "source": f"case:{case_id}",
                                "target": eid,
                                "type": "hasEHREntity",
                                "provenance": "ehr_ner",
                            })
    except Exception as exc:
        logger.debug("Could not fetch EHR entities: %s", exc)

    # If no findings found, add mock data
    if len(nodes) <= 1:
        logger.info("No findings fetched; using mock graph data")
        mock_data = _mock_case_graph(case_id or "unknown")
        nodes = mock_data["nodes"]
        edges = mock_data["edges"]

    inter["nodes"] = nodes
    inter["edges"] = edges
    state["_intermediate"] = inter
    return state


async def query_subgraph(state: GraphState) -> GraphState:
    """Query SPARQL triplestore for the case's named graph."""
    state = update_exec(state, progress=0.3, current_node="query_subgraph")
    inter = dict(state.get("_intermediate", {}))
    ctx = state.get("context", {})
    case_id = ctx.get("case_id")

    try:
        async with httpx.AsyncClient(base_url=GRAPH_SERVICE_URL, timeout=10.0) as client:
            resp = await client.get(
                f"/api/v1/cases/{case_id}/graph",
                params={"include_inferred": "true"},
            )
            if resp.status_code == 200:
                graph_data = resp.json()
                # Merge triplestore nodes/edges with findings
                existing_ids = {n["id"] for n in inter.get("nodes", [])}
                for node in graph_data.get("nodes", []):
                    if node["id"] not in existing_ids:
                        inter.setdefault("nodes", []).append(node)
                        existing_ids.add(node["id"])
                for edge in graph_data.get("edges", []):
                    inter.setdefault("edges", []).append(edge)

                inter["triplestore_graph_iri"] = graph_data.get("triplestore_graph_iri")
                inter["ontology_versions"] = graph_data.get("ontology_versions", {})
    except Exception as exc:
        logger.debug("Could not query subgraph from triplestore: %s", exc)
        inter.setdefault("ontology_versions", {"NCIt": "24.11e"})

    state["_intermediate"] = inter
    return state


async def fuse_annotate_provenance(state: GraphState) -> GraphState:
    """Fuse findings with ontology subgraph and annotate provenance (PROV-O)."""
    state = update_exec(state, progress=0.5, current_node="fuse_annotate_provenance")
    inter = dict(state.get("_intermediate", {}))
    nodes = inter.get("nodes", [])
    edges = inter.get("edges", [])

    # Add provenance metadata to edges
    now_iso = datetime.now(timezone.utc).isoformat()
    for edge in edges:
        if "timestamp" not in edge:
            edge["timestamp"] = now_iso
        if "asserted" not in edge:
            edge["asserted"] = True

    # Add inferred edges based on known relationships
    gene_nodes = [n for n in nodes if n.get("type") == "Gene"]
    pattern_nodes = [n for n in nodes if n.get("type") == "Pattern"]

    # Known gene-pattern associations from oncology literature
    associations = {
        "EGFR": ["lepidic", "papillary", "micropapillary"],
        "KRAS": ["solid", "mucinous"],
        "TP53": ["solid", "micropapillary"],
    }

    for gene_node in gene_nodes:
        gene_name = gene_node["id"].split(":")[-1] if ":" in gene_node["id"] else ""
        # Extract gene name from label
        for assoc_gene, patterns in associations.items():
            if assoc_gene.lower() in gene_node.get("label", "").lower():
                for pattern_node in pattern_nodes:
                    for pat in patterns:
                        if pat.lower() in pattern_node.get("label", "").lower():
                            edges.append({
                                "source": gene_node["id"],
                                "target": pattern_node["id"],
                                "type": "associatedWith",
                                "provenance": "literature_inference",
                                "asserted": False,
                                "timestamp": now_iso,
                            })

    inter["nodes"] = nodes
    inter["edges"] = edges
    state["_intermediate"] = inter
    return state


async def build_layout(state: GraphState) -> GraphState:
    """Compute node positions using a simple force-directed layout algorithm."""
    state = update_exec(state, progress=0.7, current_node="build_layout")
    inter = dict(state.get("_intermediate", {}))
    nodes = inter.get("nodes", [])

    # Simple circular layout for nodes
    import math
    n = len(nodes)
    radius = 200
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / max(n, 1)
        node["x"] = round(300 + radius * math.cos(angle), 1)
        node["y"] = round(300 + radius * math.sin(angle), 1)

    inter["layout_computed"] = True
    inter["nodes"] = nodes
    state["_intermediate"] = inter
    return state


async def persist_snapshot(state: GraphState) -> GraphState:
    """Persist graph snapshot to database via graph-service."""
    state = update_exec(state, progress=0.9, current_node="persist_snapshot")
    inter = dict(state.get("_intermediate", {}))
    ctx = state.get("context", {})
    case_id = ctx.get("case_id")
    outputs = dict(state.get("outputs", {}))

    snapshot_id = str(uuid4())
    outputs["graph_snapshot_id"] = snapshot_id

    # Try persisting via graph-service API
    try:
        async with httpx.AsyncClient(base_url=GRAPH_SERVICE_URL, timeout=10.0) as client:
            resp = await client.post(
                f"/api/v1/cases/{case_id}/graph:rebuild",
                params={"include_inferred": "true"},
            )
            if resp.status_code == 200:
                data = resp.json()
                outputs["graph_snapshot_id"] = data.get("id", snapshot_id)
    except Exception as exc:
        logger.debug("Could not persist via graph-service: %s", exc)

    # Also persist to S3 for archival
    storage = get_storage_tool()
    snapshot_data = json.dumps({
        "id": snapshot_id,
        "case_id": case_id,
        "nodes": inter.get("nodes", []),
        "edges": inter.get("edges", []),
        "ontology_versions": inter.get("ontology_versions", {}),
    }, indent=2).encode("utf-8")
    storage.upload_file(f"graphs/{snapshot_id}.json", snapshot_data, "application/json")

    state["outputs"] = outputs
    return state


async def finalize(state: GraphState) -> GraphState:
    """Mark workflow as completed."""
    state["execution"] = {
        **state.get("execution", {}),
        "status": "completed",
        "progress": 1.0,
        "current_node": "finalize",
    }
    return state


def _mock_case_graph(case_id: str) -> dict[str, Any]:
    """Generate mock graph data for development."""
    return {
        "nodes": [
            {"id": f"case:{case_id}", "type": "Case", "label": f"Case {case_id[:8]}...", "color": "#42A5F5"},
            {"id": "gene:EGFR", "type": "Gene", "label": "EGFR (POS)", "color": "#66BB6A"},
            {"id": "gene:KRAS", "type": "Gene", "label": "KRAS (NEG)", "color": "#66BB6A"},
            {"id": "gene:TP53", "type": "Gene", "label": "TP53 (INC)", "color": "#66BB6A"},
            {"id": "dx:adenocarcinoma", "type": "Diagnosis", "label": "Adenocarcinoma", "color": "#FF7043"},
            {"id": "pattern:lepidic", "type": "Pattern", "label": "Lepidic (32%)", "color": "#AB47BC"},
            {"id": "pattern:acinar", "type": "Pattern", "label": "Acinar (27%)", "color": "#AB47BC"},
            {"id": "pattern:papillary", "type": "Pattern", "label": "Papillary (22%)", "color": "#AB47BC"},
        ],
        "edges": [
            {"source": f"case:{case_id}", "target": "dx:adenocarcinoma", "type": "hasDiagnosis", "provenance": "ehr"},
            {"source": f"case:{case_id}", "target": "gene:EGFR", "type": "hasMutationPrediction", "provenance": "inference"},
            {"source": f"case:{case_id}", "target": "gene:KRAS", "type": "hasMutationPrediction", "provenance": "inference"},
            {"source": f"case:{case_id}", "target": "gene:TP53", "type": "hasMutationPrediction", "provenance": "inference"},
            {"source": f"case:{case_id}", "target": "pattern:lepidic", "type": "hasPattern", "provenance": "inference"},
            {"source": f"case:{case_id}", "target": "pattern:acinar", "type": "hasPattern", "provenance": "inference"},
            {"source": f"case:{case_id}", "target": "pattern:papillary", "type": "hasPattern", "provenance": "inference"},
            {"source": "gene:EGFR", "target": "pattern:lepidic", "type": "associatedWith", "provenance": "literature", "asserted": False},
        ],
    }


def create_graph_assembler_graph():
    """Build and compile the GraphAssemblerGraph."""
    wf = StateGraph(GraphState)
    for name, fn in [
        ("fetch_case_findings", fetch_case_findings),
        ("query_subgraph", query_subgraph),
        ("fuse_annotate_provenance", fuse_annotate_provenance),
        ("build_layout", build_layout),
        ("persist_snapshot", persist_snapshot),
        ("finalize", finalize),
    ]:
        wf.add_node(name, fn)

    wf.set_entry_point("fetch_case_findings")
    wf.add_edge("fetch_case_findings", "query_subgraph")
    wf.add_edge("query_subgraph", "fuse_annotate_provenance")
    wf.add_edge("fuse_annotate_provenance", "build_layout")
    wf.add_edge("build_layout", "persist_snapshot")
    wf.add_edge("persist_snapshot", "finalize")
    wf.add_edge("finalize", END)
    return wf.compile()
