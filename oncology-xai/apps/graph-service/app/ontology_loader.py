"""Build curated knowledge graph for lung adenocarcinoma.

Uses real ontology IRIs (NCIt, MONDO, DOID, ChEBI) and adds cross-domain
relationships (pattern → gene → treatment → diagnosis) based on established
clinical evidence from OncoKB, CIViC, and published literature.

Individual OWL files only contain taxonomy (subClassOf) — they do NOT
encode pattern↔gene or gene↔treatment associations.  This module adds
those relationships as a curated knowledge layer on top of the ontology
identifiers, and optionally enriches labels from parsed OWL files.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Helper: IRI builders
# ──────────────────────────────────────────────────────────────────────

def _ncit(code: str) -> str:
    return f"http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#{code}"

def _mondo(code: str) -> str:
    return f"http://purl.obolibrary.org/obo/MONDO_{code}"

def _doid(code: str) -> str:
    return f"http://purl.obolibrary.org/obo/DOID_{code}"

def _chebi(code: str) -> str:
    return f"http://purl.obolibrary.org/obo/CHEBI_{code}"


def _iri_to_id(iri: str) -> str:
    if "Thesaurus.owl#" in iri:
        return "ncit:" + iri.split("#")[-1]
    if "purl.obolibrary.org/obo/" in iri:
        frag = iri.split("/")[-1]
        return frag.replace("_", ":")
    if iri.startswith("drug:") or iri.startswith("case:") or iri.startswith("stage:"):
        return iri
    return iri.split("/")[-1].replace("#", ":")


# ──────────────────────────────────────────────────────────────────────
# Curated knowledge: entities
# ──────────────────────────────────────────────────────────────────────

CURATED_NODES: dict[str, dict] = {
    # ── Diagnosis ──
    _ncit("C2852"):     {"label": "Adenocarcinoma",            "type": "diagnosis"},
    _ncit("C2926"):     {"label": "Non-Small Cell Lung Cancer","type": "diagnosis"},
    _mondo("0005233"):  {"label": "NSCLC (MONDO)",             "type": "diagnosis"},

    # ── Histologic patterns (WHO 2021 LUAD subtypes) ──
    _ncit("C128847"):   {"label": "Lepidic Pattern",           "type": "pattern"},
    _ncit("C128848"):   {"label": "Acinar Pattern",            "type": "pattern"},
    _ncit("C128849"):   {"label": "Papillary Pattern",         "type": "pattern"},
    _ncit("C128850"):   {"label": "Micropapillary Pattern",    "type": "pattern"},
    _ncit("C128851"):   {"label": "Solid Pattern",             "type": "pattern"},
    # Mucinous (invasive mucinous adenocarcinoma)
    _ncit("C136494"):   {"label": "Mucinous Pattern",          "type": "pattern"},

    # ── Genes / Biomarkers ──
    _ncit("C17757"):    {"label": "EGFR",                      "type": "gene"},
    _ncit("C17383"):    {"label": "KRAS",                      "type": "gene"},
    _ncit("C17387"):    {"label": "TP53",                      "type": "gene"},
    _ncit("C20316"):    {"label": "ALK",                       "type": "gene"},
    _ncit("C101480"):   {"label": "ROS1",                      "type": "gene"},
    _ncit("C51549"):    {"label": "BRAF",                      "type": "gene"},
    _ncit("C17735"):    {"label": "MET",                       "type": "gene"},
    _ncit("C52544"):    {"label": "RET",                       "type": "gene"},
    _ncit("C18449"):    {"label": "HER2 (ERBB2)",              "type": "gene"},

    # ── Treatments / Drugs (FDA-approved for NSCLC, from OncoKB/NCIt) ──
    "drug:erlotinib":    {"label": "Erlotinib",       "type": "treatment", "iri": _ncit("C65530")},
    "drug:gefitinib":    {"label": "Gefitinib",       "type": "treatment", "iri": _ncit("C1855")},
    "drug:afatinib":     {"label": "Afatinib",        "type": "treatment", "iri": _ncit("C66940")},
    "drug:osimertinib":  {"label": "Osimertinib",     "type": "treatment", "iri": _ncit("C102402")},
    "drug:sotorasib":    {"label": "Sotorasib",       "type": "treatment", "iri": _ncit("C168990")},
    "drug:adagrasib":    {"label": "Adagrasib",       "type": "treatment", "iri": _ncit("C177693")},
    "drug:crizotinib":   {"label": "Crizotinib",      "type": "treatment", "iri": _ncit("C71610")},
    "drug:alectinib":    {"label": "Alectinib",       "type": "treatment", "iri": _ncit("C97660")},
    "drug:lorlatinib":   {"label": "Lorlatinib",      "type": "treatment", "iri": _ncit("C120299")},
    "drug:entrectinib":  {"label": "Entrectinib",     "type": "treatment", "iri": _ncit("C120226")},
    "drug:dabrafenib":   {"label": "Dabrafenib",      "type": "treatment", "iri": _ncit("C82386")},
    "drug:trametinib":   {"label": "Trametinib",      "type": "treatment", "iri": _ncit("C77908")},
    "drug:capmatinib":   {"label": "Capmatinib",      "type": "treatment", "iri": _ncit("C116379")},
    "drug:selpercatinib": {"label": "Selpercatinib",  "type": "treatment", "iri": _ncit("C148138")},
    "drug:trastuzumab_dxd": {"label": "Trastuzumab Deruxtecan", "type": "treatment", "iri": _ncit("C152070")},

    # ── Staging (simplified) ──
    "stage:I":   {"label": "Stage I",   "type": "stage"},
    "stage:II":  {"label": "Stage II",  "type": "stage"},
    "stage:III": {"label": "Stage III", "type": "stage"},
    "stage:IV":  {"label": "Stage IV",  "type": "stage"},
}


# ──────────────────────────────────────────────────────────────────────
# Curated knowledge: relationships (edges)
# Evidence sources: OncoKB, CIViC, WHO 2021, TCGA, NCCN Guidelines
# ──────────────────────────────────────────────────────────────────────

CURATED_EDGES: list[dict] = [
    # ── Taxonomy ──
    {"s": _ncit("C2852"),  "t": _ncit("C2926"),  "label": "subClassOf",      "prov": "NCIt"},
    {"s": _ncit("C2926"),  "t": _mondo("0005233"), "label": "equivalentClass", "prov": "MONDO"},

    # ── Patterns → Diagnosis (WHO classification) ──
    {"s": _ncit("C128847"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},
    {"s": _ncit("C128848"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},
    {"s": _ncit("C128849"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},
    {"s": _ncit("C128850"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},
    {"s": _ncit("C128851"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},
    {"s": _ncit("C136494"), "t": _ncit("C2852"), "label": "subtypeOf",       "prov": "WHO-2021"},

    # ── Patterns → Genes (morphology-molecular correlation, TCGA/literature) ──
    # Lepidic: strongly associated with EGFR (TCGA 2014, Kadota et al.)
    {"s": _ncit("C128847"), "t": _ncit("C17757"), "label": "associatedWithMutation", "prov": "TCGA/OncoKB", "type": "inferred"},
    # Acinar: associated with EGFR and KRAS
    {"s": _ncit("C128848"), "t": _ncit("C17757"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    {"s": _ncit("C128848"), "t": _ncit("C17383"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    # Papillary: associated with EGFR, BRAF
    {"s": _ncit("C128849"), "t": _ncit("C17757"), "label": "associatedWithMutation", "prov": "TCGA/OncoKB", "type": "inferred"},
    {"s": _ncit("C128849"), "t": _ncit("C51549"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    # Micropapillary: associated with EGFR, ALK, poor prognosis
    {"s": _ncit("C128850"), "t": _ncit("C17757"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    {"s": _ncit("C128850"), "t": _ncit("C20316"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    # Solid: associated with KRAS, TP53, poor prognosis
    {"s": _ncit("C128851"), "t": _ncit("C17383"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    {"s": _ncit("C128851"), "t": _ncit("C17387"), "label": "associatedWithMutation", "prov": "TCGA/CIViC",  "type": "inferred"},
    # Mucinous: strongly associated with KRAS
    {"s": _ncit("C136494"), "t": _ncit("C17383"), "label": "associatedWithMutation", "prov": "TCGA/OncoKB", "type": "inferred"},

    # ── Genes → Treatments (OncoKB / NCCN Guidelines, FDA-approved) ──
    # EGFR → TKIs
    {"s": _ncit("C17757"), "t": "drug:erlotinib",   "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C17757"), "t": "drug:gefitinib",   "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C17757"), "t": "drug:afatinib",    "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C17757"), "t": "drug:osimertinib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    # KRAS G12C → targeted therapies
    {"s": _ncit("C17383"), "t": "drug:sotorasib",   "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C17383"), "t": "drug:adagrasib",   "label": "treatedWith", "prov": "OncoKB/FDA"},
    # ALK → inhibitors
    {"s": _ncit("C20316"), "t": "drug:crizotinib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C20316"), "t": "drug:alectinib",   "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C20316"), "t": "drug:lorlatinib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    # ROS1 → inhibitors
    {"s": _ncit("C101480"), "t": "drug:crizotinib", "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C101480"), "t": "drug:entrectinib", "label": "treatedWith", "prov": "OncoKB/FDA"},
    # BRAF V600E → dabrafenib+trametinib
    {"s": _ncit("C51549"), "t": "drug:dabrafenib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    {"s": _ncit("C51549"), "t": "drug:trametinib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    # MET → capmatinib
    {"s": _ncit("C17735"), "t": "drug:capmatinib",  "label": "treatedWith", "prov": "OncoKB/FDA"},
    # RET → selpercatinib
    {"s": _ncit("C52544"), "t": "drug:selpercatinib", "label": "treatedWith", "prov": "OncoKB/FDA"},
    # HER2 → trastuzumab deruxtecan
    {"s": _ncit("C18449"), "t": "drug:trastuzumab_dxd", "label": "treatedWith", "prov": "OncoKB/FDA"},

    # ── Genes → mutatedIn diagnosis ──
    {"s": _ncit("C17757"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
    {"s": _ncit("C17383"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
    {"s": _ncit("C17387"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
    {"s": _ncit("C20316"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
    {"s": _ncit("C101480"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
    {"s": _ncit("C51549"), "t": _ncit("C2852"), "label": "mutatedIn", "prov": "COSMIC"},
]


# ──────────────────────────────────────────────────────────────────────
# OWL label enrichment (optional)
# ──────────────────────────────────────────────────────────────────────

def _enrich_labels_from_owl(nodes: dict[str, dict], ncit_path: str, mondo_path: str) -> None:
    """Try to replace placeholder labels with rdfs:label from OWL files."""
    try:
        from rdflib import Graph as RDFGraph, URIRef
        from rdflib.namespace import RDFS
    except ImportError:
        logger.debug("rdflib not available for label enrichment")
        return

    g = RDFGraph()
    for path_str in [ncit_path, mondo_path]:
        if not path_str or not Path(path_str).exists():
            continue
        try:
            g.parse(path_str, format="xml")
            logger.info("Parsed OWL for label enrichment: %s", path_str)
        except Exception as e:
            logger.warning("Failed to parse OWL for labels: %s", e)

    if not g:
        return

    for iri, data in nodes.items():
        if not iri.startswith("http"):
            continue
        try:
            ref = URIRef(iri)
            for label in g.objects(ref, RDFS.label):
                lbl = str(label)
                if lbl and len(lbl) < 80:
                    data["label"] = lbl
                break
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────
# Pattern name → NCIt IRI mapping
# ──────────────────────────────────────────────────────────────────────

PATTERN_NAME_TO_IRI: dict[str, str] = {
    "lepidic":       _ncit("C128847"),
    "acinar":        _ncit("C128848"),
    "papillary":     _ncit("C128849"),
    "micropapillary": _ncit("C128850"),
    "solid":         _ncit("C128851"),
    "mucinous":      _ncit("C136494"),
}

GENE_NAME_TO_IRI: dict[str, str] = {
    "EGFR": _ncit("C17757"),
    "KRAS": _ncit("C17383"),
    "TP53": _ncit("C17387"),
    "ALK":  _ncit("C20316"),
    "ROS1": _ncit("C101480"),
    "BRAF": _ncit("C51549"),
    "MET":  _ncit("C17735"),
    "RET":  _ncit("C52544"),
    "HER2": _ncit("C18449"),
    "ERBB2": _ncit("C18449"),
}


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def build_case_graph_from_ontology(
    case_id: str,
    ncit_owl_path: str = "",
    mondo_owl_path: str = "",
    *,
    pattern_results: list[dict] | None = None,
    genetic_results: list[dict] | None = None,
    discovered_relations: list[dict] | None = None,
) -> tuple[dict[str, dict], list[dict]]:
    """Build a **case-specific** knowledge graph.

    If pattern_results / genetic_results are provided, only include:
      - Patterns actually detected (percentage > 0.5%)
      - Genes associated with those patterns + genes predicted
      - Treatments for those genes
    If discovered_relations is provided, merge them into the graph.
    """
    # Determine which patterns and genes are relevant to this case
    if pattern_results:
        active_patterns = {
            p["pattern"].lower()
            for p in pattern_results
            if p.get("percentage", 0) > 0.5  # threshold: > 0.5% to include
        }
    else:
        active_patterns = None  # show all

    if genetic_results:
        active_genes_from_pred = {
            g["mutation"].upper()
            for g in genetic_results
            if g.get("status") in ("POS", "INCONCLUSIVE")
        }
    else:
        active_genes_from_pred = set()

    # Collect relevant IRIs
    relevant_pattern_iris: set[str] = set()
    relevant_gene_iris: set[str] = set()

    if active_patterns is not None:
        for pname, piri in PATTERN_NAME_TO_IRI.items():
            if pname in active_patterns:
                relevant_pattern_iris.add(piri)
    else:
        relevant_pattern_iris = set(PATTERN_NAME_TO_IRI.values())

    # Find genes associated with active patterns (from curated edges)
    for edge in CURATED_EDGES:
        if edge["label"] == "associatedWithMutation" and edge["s"] in relevant_pattern_iris:
            relevant_gene_iris.add(edge["t"])

    # Add genes from predictions
    for gname in active_genes_from_pred:
        if gname in GENE_NAME_TO_IRI:
            relevant_gene_iris.add(GENE_NAME_TO_IRI[gname])

    # Always include diagnoses
    relevant_diag_iris = {_ncit("C2852"), _ncit("C2926"), _mondo("0005233")}

    # Collect relevant treatment IRIs (from gene→treatment edges)
    relevant_treatment_ids: set[str] = set()
    for edge in CURATED_EDGES:
        if edge["label"] == "treatedWith" and edge["s"] in relevant_gene_iris:
            relevant_treatment_ids.add(edge["t"])

    # Build the allowed set of IRIs/ids
    allowed_iris = relevant_pattern_iris | relevant_gene_iris | relevant_diag_iris | relevant_treatment_ids

    # Build filtered nodes
    nodes: dict[str, dict] = {}
    for iri, meta in CURATED_NODES.items():
        if iri not in allowed_iris and iri not in relevant_treatment_ids:
            continue
        nid = _iri_to_id(iri)
        node = {
            "id": nid,
            "label": meta["label"],
            "type": meta["type"],
            "iri": iri if iri.startswith("http") else meta.get("iri"),
            "source": "ontology" if iri.startswith("http") else "curated",
        }
        # Add percentage annotation for patterns
        if meta["type"] == "pattern" and pattern_results:
            pname = meta["label"].lower().replace(" pattern", "")
            for p in pattern_results:
                if p["pattern"].lower() == pname:
                    node["score"] = round(p.get("percentage", 0), 1)
                    node["label"] = f"{meta['label']} ({p.get('percentage', 0):.1f}%)"
                    break
        # Add score for genes
        if meta["type"] == "gene" and genetic_results:
            gname = meta["label"].split(" ")[0].split("(")[0].strip().upper()
            for g in genetic_results:
                if g["mutation"].upper() == gname:
                    status = g.get("status", "?")
                    node["label"] = f"{meta['label']} [{status}]"
                    node["score"] = round(g.get("score", 0), 3)
                    break
        nodes[nid] = node

    # Build filtered edges (only between nodes that exist)
    node_ids = set(nodes.keys())
    edges: list[dict] = []
    for e in CURATED_EDGES:
        sid = _iri_to_id(e["s"])
        tid = _iri_to_id(e["t"])
        if sid in node_ids and tid in node_ids:
            edges.append({
                "source": sid,
                "target": tid,
                "label": e["label"],
                "type": e.get("type", "asserted"),
                "provenance": e["prov"],
            })

    # Add case node
    case_nid = f"case:{case_id}"
    nodes[case_nid] = {
        "id": case_nid,
        "label": f"Case {case_id[:8]}",
        "type": "case",
        "iri": None,
        "source": "system",
    }

    # Link case → diagnosis
    adeno_id = _iri_to_id(_ncit("C2852"))
    if adeno_id in node_ids:
        edges.append({
            "source": case_nid, "target": adeno_id,
            "label": "hasDiagnosis", "type": "asserted", "provenance": "ehr",
        })

    # Link case → detected patterns (with percentage as weight)
    for piri in relevant_pattern_iris:
        pid = _iri_to_id(piri)
        if pid in node_ids:
            edges.append({
                "source": case_nid, "target": pid,
                "label": "hasPattern", "type": "asserted", "provenance": "image",
            })

    # Merge discovered relations from batch DeepSearch
    discovered_count = 0
    if discovered_relations:
        for dr in discovered_relations:
            s_iri = dr.get("subject_iri", "")
            o_iri = dr.get("object_iri", "")
            if not s_iri or not o_iri:
                continue
            s_id = _iri_to_id(s_iri)
            o_id = _iri_to_id(o_iri)
            # Add nodes if not present
            if s_id not in nodes:
                nodes[s_id] = {
                    "id": s_id,
                    "label": dr.get("subject", s_id),
                    "type": dr.get("subject_type", "entity"),
                    "iri": s_iri,
                    "source": "discovered",
                }
            if o_id not in nodes:
                nodes[o_id] = {
                    "id": o_id,
                    "label": dr.get("object", o_id),
                    "type": dr.get("object_type", "entity"),
                    "iri": o_iri,
                    "source": "discovered",
                }
            # Add edge
            prov = dr.get("paper_source", "literature")
            if dr.get("paper_id"):
                prov = f"{prov}:{dr['paper_id'][:20]}"
            edges.append({
                "source": s_id,
                "target": o_id,
                "label": dr.get("predicate", "relatedTo"),
                "type": "inferred",
                "provenance": prov,
            })
            discovered_count += 1

    logger.info(
        "Built case-specific graph for %s: %d nodes, %d edges "
        "(patterns=%d, genes=%d, treatments=%d, discovered=%d)",
        case_id[:8], len(nodes), len(edges),
        len(relevant_pattern_iris), len(relevant_gene_iris),
        len(relevant_treatment_ids), discovered_count,
    )
    return nodes, edges
