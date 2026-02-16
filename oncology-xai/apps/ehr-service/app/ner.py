"""Simple NER + ontology lookup for EHR extraction.

For MVP: regex-based entity recognition with keyword dictionaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExtractedEntity:
    text: str
    entity_type: str  # DIAGNOSIS, MUTATION, PATTERN, STAGE, TREATMENT
    start: int
    end: int
    confidence: float = 1.0
    section: str | None = None


# Keyword dictionaries
MUTATIONS = {
    "EGFR": ["EGFR", "egfr", "epidermal growth factor receptor"],
    "KRAS": ["KRAS", "kras", "K-ras"],
    "TP53": ["TP53", "tp53", "p53"],
    "ALK": ["ALK", "alk"],
    "ROS1": ["ROS1", "ros1"],
}

PATTERNS = {
    "lepidic": ["lepidic", "lepídico"],
    "acinar": ["acinar"],
    "papillary": ["papillary", "papilar"],
    "micropapillary": ["micropapillary", "micropapilar"],
    "solid": ["solid", "sólido"],
    "mucinous": ["mucinous", "mucinoso"],
}

DIAGNOSES = [
    "adenocarcinoma", "carcinoma", "NSCLC", "non-small cell",
    "squamous cell", "large cell", "small cell",
    "lung cancer", "cáncer de pulmón",
]

STAGES = ["stage I", "stage II", "stage III", "stage IV", "IA", "IB", "IIA", "IIB", "IIIA", "IIIB", "IV"]


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Extract clinical entities from EHR text."""
    entities: list[ExtractedEntity] = []

    # Mutations
    for gene, keywords in MUTATIONS.items():
        for kw in keywords:
            for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=m.group(), entity_type="MUTATION",
                    start=m.start(), end=m.end(), confidence=0.95,
                ))

    # Patterns
    for pattern, keywords in PATTERNS.items():
        for kw in keywords:
            for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=m.group(), entity_type="PATTERN",
                    start=m.start(), end=m.end(), confidence=0.90,
                ))

    # Diagnoses
    for dx in DIAGNOSES:
        for m in re.finditer(re.escape(dx), text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                text=m.group(), entity_type="DIAGNOSIS",
                start=m.start(), end=m.end(), confidence=0.85,
            ))

    # Stages
    for st in STAGES:
        for m in re.finditer(r"\b" + re.escape(st) + r"\b", text, re.IGNORECASE):
            entities.append(ExtractedEntity(
                text=m.group(), entity_type="STAGE",
                start=m.start(), end=m.end(), confidence=0.80,
            ))

    # Deduplicate overlapping
    entities.sort(key=lambda e: (e.start, -e.end))
    return entities


# Simple ontology IRI mapping
ONTOLOGY_MAP: dict[str, dict[str, tuple[str, str]]] = {
    "MUTATION": {
        "EGFR": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17757"),
        "KRAS": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17383"),
        "TP53": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17387"),
    },
    "DIAGNOSIS": {
        "adenocarcinoma": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2852"),
        "NSCLC": ("MONDO", "http://purl.obolibrary.org/obo/MONDO_0005233"),
        "lung cancer": ("MONDO", "http://purl.obolibrary.org/obo/MONDO_0008903"),
    },
    "PATTERN": {
        "lepidic": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C128847"),
        "acinar": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C128848"),
        "papillary": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C128849"),
        "micropapillary": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C128850"),
        "solid": ("NCIt", "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C128851"),
    },
}


def map_entity_to_ontology(entity: ExtractedEntity) -> list[dict]:
    """Map an extracted entity to ontology IRIs."""
    mappings = []
    type_map = ONTOLOGY_MAP.get(entity.entity_type, {})
    text_lower = entity.text.lower()

    for key, (onto, iri) in type_map.items():
        if key.lower() in text_lower or text_lower in key.lower():
            mappings.append({
                "ontology": onto,
                "iri": iri,
                "label": key,
                "confidence": entity.confidence * 0.9,
                "mapping_method": "keyword_lookup",
            })

    return mappings
