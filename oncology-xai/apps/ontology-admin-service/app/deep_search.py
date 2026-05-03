"""DeepSearchUpdater pipeline — LLM-based KG enrichment.

Pipeline steps:
  1. Ingest: text/paper/KB export
  2. Extract candidate relations via LLM
  3. Entity-link to canonical IRIs (NCIt, MONDO, etc.)
  4. Deduplicate & merge evidence
  5. Validate (SHACL-like rules)
  6. Produce new KG version snapshot
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Known entity IRIs for linking
ENTITY_IRI_MAP: dict[str, dict] = {
    # Genes
    "EGFR": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17757", "type": "gene"},
    "KRAS": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C25785", "type": "gene"},
    "TP53": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17359", "type": "gene"},
    "ALK":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C20316", "type": "gene"},
    "ROS1": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C101480", "type": "gene"},
    "BRAF": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C51549", "type": "gene"},
    "MET":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C17735", "type": "gene"},
    "RET":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C52544", "type": "gene"},
    "HER2": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C18449", "type": "gene"},
    # Patterns
    "lepidic":       {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C55821", "type": "pattern"},
    "acinar":        {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C35922", "type": "pattern"},
    "papillary":     {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C35911", "type": "pattern"},
    "micropapillary": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C36181", "type": "pattern"},
    "solid":         {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C36182", "type": "pattern"},
    "cribriform":    {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C35920", "type": "pattern"},
    # Diagnoses
    "adenocarcinoma": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2852", "type": "diagnosis"},
    "NSCLC":          {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C2926", "type": "diagnosis"},
    # Drugs
    "erlotinib":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C65530", "type": "treatment"},
    "osimertinib": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C116377", "type": "treatment"},
    "sotorasib":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C154287", "type": "treatment"},
    "crizotinib": {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C71610", "type": "treatment"},
    "alectinib":  {"iri": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C101790", "type": "treatment"},
}

EXTRACT_SYSTEM_PROMPT = """You are a biomedical knowledge extraction system.
Given a text about lung cancer, extract structured relations as JSON.
Each relation must have: subject, predicate, object, evidence_quote.
Predicates: associatedWithMutation, treatedWith, subtypeOf, mutatedIn, resistantTo, biomarkerFor.
Return a JSON array of relations. Example:
[{"subject": "lepidic pattern", "predicate": "associatedWithMutation", "object": "EGFR", "evidence_quote": "..."}]"""

VALIDATE_RULES = [
    # (subject_type, predicate, object_type)
    ("pattern", "associatedWithMutation", "gene"),
    ("pattern", "subtypeOf", "diagnosis"),
    ("gene", "treatedWith", "treatment"),
    ("gene", "mutatedIn", "diagnosis"),
    ("gene", "biomarkerFor", "diagnosis"),
    ("treatment", "resistantTo", "gene"),
]


async def extract_relations_llm(
    text: str,
    *,
    llm_provider: str = "mock",
    openai_api_key: str = "",
    anthropic_api_key: str = "",
) -> list[dict[str, Any]]:
    """Step 2: Extract candidate relations from text via LLM."""
    if llm_provider == "mock" or (not openai_api_key and not anthropic_api_key):
        return _mock_extract(text)

    user_prompt = f"Extract biomedical relations from this text:\n\n{text[:3000]}\n\nReturn JSON array only."

    if llm_provider == "openai" and openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1500,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return _parse_llm_json(content)
        except Exception as e:
            logger.warning("OpenAI extraction failed: %s", e)

    if llm_provider == "anthropic" and anthropic_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 1500,
                        "system": EXTRACT_SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                if resp.status_code == 200:
                    for block in resp.json().get("content", []):
                        if block.get("type") == "text":
                            return _parse_llm_json(block["text"])
        except Exception as e:
            logger.warning("Anthropic extraction failed: %s", e)

    return _mock_extract(text)


def entity_link(relations: list[dict]) -> list[dict]:
    """Step 3: Link extracted entity names to canonical IRIs."""
    linked = []
    for rel in relations:
        subj_name = rel.get("subject", "").strip()
        obj_name = rel.get("object", "").strip()

        subj_info = _find_entity(subj_name)
        obj_info = _find_entity(obj_name)

        linked.append({
            **rel,
            "subject_iri": subj_info.get("iri") if subj_info else None,
            "subject_type": subj_info.get("type") if subj_info else "unknown",
            "object_iri": obj_info.get("iri") if obj_info else None,
            "object_type": obj_info.get("type") if obj_info else "unknown",
            "linked": bool(subj_info and obj_info),
        })
    return linked


def deduplicate(relations: list[dict]) -> list[dict]:
    """Step 4: Deduplicate relations by (subject_iri, predicate, object_iri)."""
    seen: set[tuple] = set()
    result = []
    for rel in relations:
        key = (rel.get("subject_iri"), rel.get("predicate"), rel.get("object_iri"))
        if key in seen or not all(key):
            continue
        seen.add(key)
        result.append(rel)
    return result


def validate_relations(relations: list[dict]) -> dict:
    """Step 5: Validate relations against SHACL-like rules."""
    valid = []
    invalid = []
    for rel in relations:
        st = rel.get("subject_type", "")
        pred = rel.get("predicate", "")
        ot = rel.get("object_type", "")
        rule_match = any(
            st == r[0] and pred == r[1] and ot == r[2]
            for r in VALIDATE_RULES
        )
        if rule_match and rel.get("linked"):
            valid.append({**rel, "validation": "PASS"})
        else:
            reason = "no_matching_rule" if not rule_match else "unlinked_entity"
            invalid.append({**rel, "validation": "FAIL", "validation_reason": reason})
    return {"valid": valid, "invalid": invalid}


async def run_pipeline(
    text: str,
    source_type: str = "text",
    *,
    llm_provider: str = "mock",
    openai_api_key: str = "",
    anthropic_api_key: str = "",
) -> dict[str, Any]:
    """Run complete DeepSearch pipeline."""
    # Step 2: Extract
    raw_relations = await extract_relations_llm(
        text, llm_provider=llm_provider,
        openai_api_key=openai_api_key, anthropic_api_key=anthropic_api_key,
    )
    # Step 3: Link
    linked = entity_link(raw_relations)
    # Step 4: Dedup
    deduped = deduplicate(linked)
    # Step 5: Validate
    validation = validate_relations(deduped)

    return {
        "raw_count": len(raw_relations),
        "linked_count": sum(1 for r in linked if r.get("linked")),
        "deduped_count": len(deduped),
        "valid_count": len(validation["valid"]),
        "invalid_count": len(validation["invalid"]),
        "valid_relations": validation["valid"],
        "invalid_relations": validation["invalid"],
    }


# ── Helpers ──

def _find_entity(name: str) -> dict | None:
    name_lower = name.lower().strip()
    # Direct match
    if name.upper() in ENTITY_IRI_MAP:
        return ENTITY_IRI_MAP[name.upper()]
    if name_lower in ENTITY_IRI_MAP:
        return ENTITY_IRI_MAP[name_lower]
    # Partial match
    for key, val in ENTITY_IRI_MAP.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return val
    return None


def _parse_llm_json(text: str) -> list[dict]:
    """Parse JSON array from LLM output (handles markdown fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def _mock_extract(text: str) -> list[dict]:
    """Generate mock relations from text keywords."""
    relations = []
    text_lower = text.lower()
    pairs = [
        ("lepidic", "EGFR", "associatedWithMutation"),
        ("acinar", "KRAS", "associatedWithMutation"),
        ("solid", "TP53", "associatedWithMutation"),
        ("papillary", "BRAF", "associatedWithMutation"),
        ("EGFR", "osimertinib", "treatedWith"),
        ("KRAS", "sotorasib", "treatedWith"),
        ("ALK", "crizotinib", "treatedWith"),
    ]
    for subj, obj, pred in pairs:
        if subj.lower() in text_lower or obj.lower() in text_lower:
            relations.append({
                "subject": subj, "predicate": pred, "object": obj,
                "evidence_quote": f"Extracted from input text (mock): {subj} → {obj}",
            })
    if not relations:
        relations = [
            {"subject": "solid pattern", "predicate": "associatedWithMutation", "object": "KRAS",
             "evidence_quote": "Mock: solid pattern associated with KRAS mutations in LUAD"},
        ]
    return relations
