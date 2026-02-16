"""SPARQL query helpers for Fuseki."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def sparql_query(fuseki_url: str, dataset: str, query: str) -> list[dict]:
    """Execute SPARQL SELECT query and return bindings."""
    url = f"{fuseki_url}/{dataset}/sparql"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        results = resp.json()
        bindings = results.get("results", {}).get("bindings", [])
        return [
            {k: v.get("value") for k, v in row.items()}
            for row in bindings
        ]


async def get_case_subgraph(
    fuseki_url: str,
    dataset: str,
    case_id: str,
    depth: int = 2,
    *,
    from_ontology: bool = False,
    **kwargs: Any,
) -> dict:
    """Build a subgraph for a case. If from_ontology=True, use OWL files only (skip Fuseki)."""
    from app.config import settings
    from app.ontology_loader import build_case_graph_from_ontology

    # Grafo curado dinámico (usa IRIs reales, no parsea OWL — instantáneo)
    if from_ontology:
        nodes, edges = build_case_graph_from_ontology(
            case_id,
            pattern_results=kwargs.get("pattern_results"),
            genetic_results=kwargs.get("genetic_results"),
            discovered_relations=kwargs.get("discovered_relations"),
        )
        if not nodes:
            nodes, edges = _mock_case_graph(case_id)
            logger.warning("Curated graph returned empty, using mock graph")
            return {"nodes": list(nodes.values()), "edges": edges, "source": "mock", "source_message": "Grafo mockup de demostración."}
        is_dynamic = kwargs.get("pattern_results") is not None
        has_discovered = bool(kwargs.get("discovered_relations"))
        msg = "Grafo dinámico basado en resultados del caso"
        if has_discovered:
            msg += " + relaciones descubiertas por DeepSearch (literatura)"
        msg += " (NCIt/MONDO/OncoKB/CIViC/COSMIC/WHO)."
        logger.info("Built curated knowledge graph for case %s (dynamic=%s, discovered=%s)", case_id, is_dynamic, has_discovered)
        return {"nodes": list(nodes.values()), "edges": edges, "source": "curated", "source_message": msg}

    # Query case graph from Fuseki
    query = f"""
    SELECT ?s ?p ?o
    WHERE {{
        GRAPH <graph:case:{case_id}> {{
            ?s ?p ?o .
        }}
    }}
    LIMIT 500
    """
    fuseki_error: str | None = None
    try:
        bindings = await sparql_query(fuseki_url, dataset, query)
    except Exception as e:
        fuseki_error = str(e)
        logger.warning("SPARQL query failed: %s — returning mock/OWL graph", e)
        bindings = []

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for row in bindings:
        s, p, o = row.get("s", ""), row.get("p", ""), row.get("o", "")
        if s and s not in nodes:
            nodes[s] = {"id": s, "label": s.rsplit("/", 1)[-1], "type": "entity", "iri": s, "source": "ontology"}
        if o and o.startswith("http") and o not in nodes:
            nodes[o] = {"id": o, "label": o.rsplit("/", 1)[-1], "type": "entity", "iri": o, "source": "ontology"}
        if s and o:
            edges.append({
                "source": s, "target": o,
                "label": p.rsplit("/", 1)[-1] if "/" in p else p,
                "type": "asserted",
                "provenance": "fuseki",
            })

    # If empty: try real OWL ontologies first, then fall back to mock
    if not nodes:
        reason = f"No se encontró grafo en Fuseki para este caso (GRAPH <graph:case:{case_id}> vacío)."
        if fuseki_error:
            reason += f" Fuseki devolvió: {fuseki_error[:200]}"
        ncit = getattr(settings, "ncit_owl_path", "") or ""
        mondo = getattr(settings, "mondo_owl_path", "") or ""
        nodes, edges = build_case_graph_from_ontology(case_id, ncit_owl_path=ncit, mondo_owl_path=mondo)
        if not nodes:
            nodes, edges = _mock_case_graph(case_id)
            logger.info("Using mock graph: %s", reason)
            return {"nodes": list(nodes.values()), "edges": edges, "source": "mock", "source_message": reason + " OWL no devolvió datos; se muestra grafo mockup de demostración."}
        logger.info("Graph built from OWL ontologies (real)")
        nodes = dict(nodes)
        return {"nodes": list(nodes.values()), "edges": edges, "source": "owl", "source_message": reason + " Se usó grafo desde ontologías OWL (NCIt/MONDO)."}
    return {"nodes": list(nodes.values()), "edges": edges, "source": "fuseki", "source_message": "Grafo cargado desde Fuseki (triplestore)."}


def _mock_case_graph(case_id: str) -> tuple[dict, list]:
    """Generate a representative mock graph for demo."""
    nodes = {
        "case": {"id": f"case:{case_id}", "label": f"Case {case_id[:8]}", "type": "case", "iri": None, "source": "system"},
        "tp53": {"id": "ncit:C17387", "label": "TP53", "type": "gene", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17387", "source": "ontology"},
        "egfr": {"id": "ncit:C17757", "label": "EGFR", "type": "gene", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17757", "source": "ontology"},
        "adeno": {"id": "ncit:C2852", "label": "Adenocarcinoma", "type": "diagnosis", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2852", "source": "ontology"},
        "lepidic": {"id": "pattern:lepidic", "label": "Lepidic", "type": "pattern", "iri": None, "source": "image"},
        "acinar": {"id": "pattern:acinar", "label": "Acinar", "type": "pattern", "iri": None, "source": "image"},
        "papillary": {"id": "pattern:papillary", "label": "Papillary", "type": "pattern", "iri": None, "source": "image"},
        "nsclc": {"id": "mondo:0005233", "label": "NSCLC", "type": "diagnosis", "iri": "http://purl.obolibrary.org/obo/MONDO_0005233", "source": "ontology"},
    }
    edges = [
        {"source": f"case:{case_id}", "target": "ncit:C2852", "label": "hasDiagnosis", "type": "asserted", "provenance": "ehr"},
        {"source": f"case:{case_id}", "target": "pattern:lepidic", "label": "hasPattern", "type": "asserted", "provenance": "image"},
        {"source": f"case:{case_id}", "target": "pattern:acinar", "label": "hasPattern", "type": "asserted", "provenance": "image"},
        {"source": f"case:{case_id}", "target": "pattern:papillary", "label": "hasPattern", "type": "asserted", "provenance": "image"},
        {"source": "ncit:C2852", "target": "mondo:0005233", "label": "subClassOf", "type": "asserted", "provenance": "ontology"},
        {"source": "pattern:lepidic", "target": "ncit:C17387", "label": "associatedWith", "type": "inferred", "provenance": "thesis"},
        {"source": "pattern:acinar", "target": "ncit:C17757", "label": "associatedWith", "type": "inferred", "provenance": "thesis"},
        {"source": "ncit:C17387", "target": "ncit:C2852", "label": "mutatedIn", "type": "asserted", "provenance": "ontology"},
    ]
    return nodes, edges
