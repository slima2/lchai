"""EHRToOntologyGraph — LangGraph workflow (DERCAS 13.1.2).

NormalizeEHR → ExtractEntities → LookupCandidates → Disambiguate →
BuildEvidencePack → PersistEntitiesMappings → Finalize
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx
from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_exec

logger = logging.getLogger(__name__)

EHR_SERVICE_URL = os.getenv("EHR_SERVICE_URL", "http://localhost:8004")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8005")

# ── NER patterns (mirrors ehr-service/app/ner.py) ────────────────────

MUTATION_KEYWORDS = {
    "EGFR": r"\bEGFR\b",
    "KRAS": r"\bKRAS\b",
    "TP53": r"\bTP53\b",
    "ALK": r"\bALK\b",
    "ROS1": r"\bROS1\b",
    "BRAF": r"\bBRAF\b",
}

PATTERN_KEYWORDS = {
    "lepidic": r"\blepidic\b",
    "acinar": r"\bacinar\b",
    "papillary": r"\bpapillary\b",
    "micropapillary": r"\bmicro[\-]?papillary\b",
    "solid": r"\bsolid\b",
    "cribriform": r"\bcribriform\b",
}

DIAGNOSIS_KEYWORDS = {
    "adenocarcinoma": r"\badenocarcinoma\b",
    "squamous cell carcinoma": r"\bsquamous\s+cell\s+carcinoma\b",
    "NSCLC": r"\bNSCLC\b",
    "non-small cell": r"\bnon[\-\s]small\s+cell\b",
}

STAGE_KEYWORDS = {
    "Stage I": r"\bstage\s+I\b",
    "Stage II": r"\bstage\s+II\b",
    "Stage III": r"\bstage\s+III\b",
    "Stage IV": r"\bstage\s+IV\b",
}

# Ontology IRI mappings
ONTOLOGY_MAP: dict[str, dict[str, str]] = {
    "EGFR": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17757", "label": "EGFR Gene"},
    "KRAS": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C25785", "label": "KRAS Gene"},
    "TP53": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17359", "label": "TP53 Gene"},
    "ALK": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C20316", "label": "ALK Gene"},
    "ROS1": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C101480", "label": "ROS1 Gene"},
    "adenocarcinoma": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2852", "label": "Adenocarcinoma"},
    "NSCLC": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2926", "label": "Non-Small Cell Lung Carcinoma"},
    "lepidic": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C55821", "label": "Lepidic Growth Pattern"},
    "acinar": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C35922", "label": "Acinar Pattern"},
    "papillary": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C35911", "label": "Papillary Growth Pattern"},
    "micropapillary": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C36181", "label": "Micropapillary Growth Pattern"},
    "solid": {"ontology": "NCIt", "iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C36182", "label": "Solid Growth Pattern"},
}


async def normalize_ehr(state: GraphState) -> GraphState:
    """Normalize EHR text: whitespace, encoding, and section detection."""
    state = update_exec(state, status="running", progress=0.1, current_node="normalize_ehr")
    ehr_text = state.get("_ehr_text", "")
    if not ehr_text:
        ehr_text = state.get("inputs", {}).get("ehr_text", "")

    # Basic normalization
    ehr_text = ehr_text.strip()
    ehr_text = re.sub(r"\s+", " ", ehr_text)
    ehr_text = ehr_text.replace("\u00a0", " ")  # Non-breaking space

    state["_ehr_text"] = ehr_text
    inter = dict(state.get("_intermediate", {}))
    inter["ehr_normalized"] = True
    inter["ehr_length"] = len(ehr_text)
    state["_intermediate"] = inter
    return state


async def extract_entities(state: GraphState) -> GraphState:
    """Extract named entities from EHR text using regex-based NER."""
    state = update_exec(state, progress=0.3, current_node="extract_entities")
    ehr_text = state.get("_ehr_text", "")
    entities: list[dict[str, Any]] = []

    # Extract mutations
    for gene, pattern in MUTATION_KEYWORDS.items():
        for match in re.finditer(pattern, ehr_text, re.IGNORECASE):
            entities.append({
                "text": match.group(),
                "type": "MUTATION",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95,
                "normalized": gene,
            })

    # Extract patterns
    for pname, pattern in PATTERN_KEYWORDS.items():
        for match in re.finditer(pattern, ehr_text, re.IGNORECASE):
            entities.append({
                "text": match.group(),
                "type": "PATTERN",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.90,
                "normalized": pname,
            })

    # Extract diagnoses
    for dx, pattern in DIAGNOSIS_KEYWORDS.items():
        for match in re.finditer(pattern, ehr_text, re.IGNORECASE):
            entities.append({
                "text": match.group(),
                "type": "DIAGNOSIS",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.90,
                "normalized": dx,
            })

    # Extract stages
    for stage, pattern in STAGE_KEYWORDS.items():
        for match in re.finditer(pattern, ehr_text, re.IGNORECASE):
            entities.append({
                "text": match.group(),
                "type": "STAGE",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.85,
                "normalized": stage,
            })

    outputs = dict(state.get("outputs", {}))
    outputs["entities"] = entities
    state["outputs"] = outputs
    logger.info("Extracted %d entities from EHR text", len(entities))
    return state


async def lookup_candidates(state: GraphState) -> GraphState:
    """Lookup ontology candidates for each extracted entity."""
    state = update_exec(state, progress=0.5, current_node="lookup_candidates")
    outputs = dict(state.get("outputs", {}))
    entities = outputs.get("entities", [])
    inter = dict(state.get("_intermediate", {}))

    candidates: list[dict[str, Any]] = []
    for entity in entities:
        normalized = entity.get("normalized", entity.get("text", ""))
        if normalized in ONTOLOGY_MAP:
            mapping = ONTOLOGY_MAP[normalized]
            candidates.append({
                "entity_text": entity["text"],
                "entity_type": entity["type"],
                "ontology": mapping["ontology"],
                "iri": mapping["iri"],
                "label": mapping["label"],
                "confidence": entity.get("confidence", 0.5) * 0.95,
                "method": "keyword_lookup",
            })

    # Try SPARQL lookup against Fuseki for unmapped entities
    unmapped = [e for e in entities if e.get("normalized", "") not in ONTOLOGY_MAP]
    if unmapped:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for entity in unmapped:
                    resp = await client.get(
                        f"{GRAPH_SERVICE_URL}/api/v1/sparql/search",
                        params={"q": entity.get("text", ""), "limit": 3},
                    )
                    if resp.status_code == 200:
                        for hit in resp.json():
                            candidates.append({
                                "entity_text": entity["text"],
                                "entity_type": entity["type"],
                                "ontology": hit.get("ontology", "NCIt"),
                                "iri": hit.get("iri", ""),
                                "label": hit.get("label", ""),
                                "confidence": hit.get("score", 0.5),
                                "method": "sparql_search",
                            })
        except Exception as exc:
            logger.debug("SPARQL lookup failed (expected in mock mode): %s", exc)

    inter["candidates"] = candidates
    state["_intermediate"] = inter
    return state


async def disambiguate(state: GraphState) -> GraphState:
    """Disambiguate ontology candidates — pick highest confidence per entity."""
    state = update_exec(state, progress=0.6, current_node="disambiguate")
    inter = dict(state.get("_intermediate", {}))
    candidates = inter.get("candidates", [])

    # Group by entity_text, pick highest confidence
    best: dict[str, dict[str, Any]] = {}
    for c in candidates:
        key = c["entity_text"]
        if key not in best or c.get("confidence", 0) > best[key].get("confidence", 0):
            best[key] = c

    inter["disambiguated"] = list(best.values())
    state["_intermediate"] = inter
    return state


async def build_evidence_pack(state: GraphState) -> GraphState:
    """Build evidence pack with entity-mapping pairs and provenance."""
    state = update_exec(state, progress=0.7, current_node="build_evidence_pack")
    inter = dict(state.get("_intermediate", {}))
    disambiguated = inter.get("disambiguated", [])

    evidence_pack = {
        "ehr_id": state.get("inputs", {}).get("ehr_id"),
        "case_id": state.get("context", {}).get("case_id"),
        "n_entities": len(state.get("outputs", {}).get("entities", [])),
        "n_mappings": len(disambiguated),
        "provenance": "regex_ner + keyword_lookup + sparql_search",
        "mappings": disambiguated,
    }

    inter["evidence_pack"] = evidence_pack
    state["_intermediate"] = inter
    return state


async def persist_entities_mappings(state: GraphState) -> GraphState:
    """Persist entities and mappings via ehr-service API."""
    state = update_exec(state, progress=0.9, current_node="persist_entities_mappings")
    outputs = dict(state.get("outputs", {}))
    inter = dict(state.get("_intermediate", {}))

    disambiguated = inter.get("disambiguated", [])
    outputs["mappings"] = disambiguated
    state["outputs"] = outputs

    # Try persisting to ehr-service
    ehr_id = state.get("inputs", {}).get("ehr_id")
    if ehr_id:
        try:
            async with httpx.AsyncClient(base_url=EHR_SERVICE_URL, timeout=15.0) as client:
                resp = await client.post(f"/api/v1/ehr/{ehr_id}:extract-and-map")
                if resp.status_code == 200:
                    logger.info("Persisted entities/mappings via ehr-service for ehr=%s", ehr_id)
        except Exception as exc:
            logger.debug("Could not persist to ehr-service: %s", exc)

    return state


async def finalize(state: GraphState) -> GraphState:
    """Mark workflow as completed."""
    ex = dict(state.get("execution", {}))
    ex["status"] = "completed"
    ex["progress"] = 1.0
    ex["current_node"] = "finalize"
    state["execution"] = ex
    return state


def create_ehr_ontology_graph():
    """Build and compile the EHRToOntologyGraph."""
    wf = StateGraph(GraphState)
    wf.add_node("normalize_ehr", normalize_ehr)
    wf.add_node("extract_entities", extract_entities)
    wf.add_node("lookup_candidates", lookup_candidates)
    wf.add_node("disambiguate", disambiguate)
    wf.add_node("build_evidence_pack", build_evidence_pack)
    wf.add_node("persist_entities_mappings", persist_entities_mappings)
    wf.add_node("finalize", finalize)

    wf.set_entry_point("normalize_ehr")
    wf.add_edge("normalize_ehr", "extract_entities")
    wf.add_edge("extract_entities", "lookup_candidates")
    wf.add_edge("lookup_candidates", "disambiguate")
    wf.add_edge("disambiguate", "build_evidence_pack")
    wf.add_edge("build_evidence_pack", "persist_entities_mappings")
    wf.add_edge("persist_entities_mappings", "finalize")
    wf.add_edge("finalize", END)

    return wf.compile()
