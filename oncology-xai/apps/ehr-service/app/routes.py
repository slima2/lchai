"""EHR Service routes (DERCAS 9.5)."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EHRDocumentDB, EHREntityDB, EHRMappingDB
from app.ner import extract_entities, map_entity_to_ontology

router = APIRouter(prefix="/api/v1", tags=["EHR"])


@router.post("/cases/{case_id}/ehr:ingest", status_code=status.HTTP_201_CREATED)
async def ingest_ehr(case_id: str, body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    # Check version
    stmt = select(EHRDocumentDB).where(EHRDocumentDB.case_id == case_id).order_by(EHRDocumentDB.version.desc()).limit(1)
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    doc = EHRDocumentDB(
        id=str(uuid4()),
        case_id=case_id,
        version=version,
        source=body.get("source", "paste"),
        content_text=content,
        checksum=hashlib.sha256(content.encode()).hexdigest(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _doc_dict(doc)


@router.get("/cases/{case_id}/ehr/versions")
async def list_ehr_versions(case_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EHRDocumentDB).where(EHRDocumentDB.case_id == case_id).order_by(EHRDocumentDB.version.desc())
    result = await db.execute(stmt)
    return [_doc_dict(d) for d in result.scalars().all()]


@router.get("/ehr/{ehr_id}")
async def get_ehr(ehr_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(EHRDocumentDB, ehr_id)
    if not doc:
        raise HTTPException(status_code=404, detail="EHR document not found")
    return _doc_dict(doc)


@router.post("/ehr/{ehr_id}:extract-and-map", status_code=status.HTTP_200_OK)
async def extract_and_map(ehr_id: str, db: AsyncSession = Depends(get_db)):
    """Extract entities from EHR and map to ontologies."""
    doc = await db.get(EHRDocumentDB, ehr_id)
    if not doc:
        raise HTTPException(status_code=404, detail="EHR not found")

    text = doc.content_text or ""
    entities = extract_entities(text)

    created_entities = []
    created_mappings = []

    for ent in entities:
        ent_id = str(uuid4())
        ent_db = EHREntityDB(
            id=ent_id,
            ehr_id=ehr_id,
            text=ent.text,
            entity_type=ent.entity_type,
            start=ent.start,
            end=ent.end,
            confidence=ent.confidence,
            section=ent.section,
        )
        db.add(ent_db)
        created_entities.append({"entity_id": ent_id, "text": ent.text, "type": ent.entity_type})

        # Map to ontology
        mappings = map_entity_to_ontology(ent)
        for m in mappings:
            map_id = str(uuid4())
            map_db = EHRMappingDB(
                id=map_id,
                entity_id=ent_id,
                ontology=m["ontology"],
                iri=m["iri"],
                label=m["label"],
                confidence=m["confidence"],
                mapping_method=m["mapping_method"],
            )
            db.add(map_db)
            created_mappings.append({"mapping_id": map_id, "entity_id": ent_id, **m})

    await db.commit()
    return {
        "ehr_id": ehr_id,
        "entities_count": len(created_entities),
        "mappings_count": len(created_mappings),
        "entities": created_entities,
        "mappings": created_mappings,
    }


@router.get("/ehr/{ehr_id}/entities")
async def get_entities(ehr_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EHREntityDB).where(EHREntityDB.ehr_id == ehr_id)
    result = await db.execute(stmt)
    return [
        {"entity_id": e.id, "text": e.text, "type": e.entity_type, "start": e.start, "end": e.end, "confidence": e.confidence}
        for e in result.scalars().all()
    ]


@router.get("/ehr/{ehr_id}/mappings")
async def get_mappings(ehr_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EHRMappingDB).join(EHREntityDB).where(EHREntityDB.ehr_id == ehr_id)
    result = await db.execute(stmt)
    return [
        {"mapping_id": m.id, "entity_id": m.entity_id, "ontology": m.ontology, "iri": m.iri, "label": m.label, "confidence": m.confidence}
        for m in result.scalars().all()
    ]


def _doc_dict(d: EHRDocumentDB) -> dict:
    return {
        "ehr_id": d.id, "case_id": d.case_id, "version": d.version,
        "source": d.source, "checksum": d.checksum,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
