"""Patient and Case CRUD routes."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PatientDB, CaseDB

logger = logging.getLogger(__name__)

patients_router = APIRouter(prefix="/api/v1", tags=["Patients"])
cases_router = APIRouter(prefix="/api/v1", tags=["Cases"])


# ── Patients ───────────────────────────────────────────────────────────

@patients_router.post("/patients", status_code=status.HTTP_201_CREATED)
async def create_patient(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    patient = PatientDB(
        id=str(uuid4()),
        external_id=body.get("external_id"),
        demographics=body.get("demographics", {}),
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return _patient_dict(patient)


@patients_router.get("/patients")
async def list_patients(
    query: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PatientDB)
    if query:
        stmt = stmt.where(PatientDB.external_id.ilike(f"%{query}%"))
    result = await db.execute(stmt)
    return [_patient_dict(p) for p in result.scalars().all()]


@patients_router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    patient = await db.get(PatientDB, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _patient_dict(patient)


async def _cascade_delete_case(db: AsyncSession, case_id: str) -> dict[str, int]:
    """Hard-delete a case and all dependent rows in FK order.

    Returns counts per table. Caller is responsible for the surrounding transaction.
    """
    counts: dict[str, int] = {}

    rb_rows = await db.execute(text("SELECT id FROM result_bundles WHERE case_id = :c"), {"c": case_id})
    rb_ids = [r[0] for r in rb_rows.fetchall()]
    for rb in rb_ids:
        for table in ("xai_artifacts", "pattern_results", "genetic_results", "morphologic_profiles"):
            res = await db.execute(text(f"DELETE FROM {table} WHERE result_bundle_id = :rb"), {"rb": rb})
            counts[table] = counts.get(table, 0) + (res.rowcount or 0)

    res = await db.execute(text("DELETE FROM result_bundles WHERE case_id = :c"), {"c": case_id})
    counts["result_bundles"] = res.rowcount or 0
    res = await db.execute(text("DELETE FROM ml_jobs WHERE case_id = :c"), {"c": case_id})
    counts["ml_jobs"] = res.rowcount or 0
    res = await db.execute(text("DELETE FROM images WHERE case_id = :c"), {"c": case_id})
    counts["images"] = res.rowcount or 0
    res = await db.execute(text("DELETE FROM ehr_documents WHERE case_id = :c"), {"c": case_id})
    counts["ehr_documents"] = res.rowcount or 0
    res = await db.execute(text("DELETE FROM cases WHERE id = :c"), {"c": case_id})
    counts["cases"] = res.rowcount or 0
    return counts


@patients_router.delete("/patients/{patient_id}", status_code=status.HTTP_200_OK)
async def delete_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Hard-delete a patient and ALL their cases and dependent rows.

    Intended primarily for rollback after a failed upload that left an orphan
    patient/case behind. Use with care.
    """
    patient = await db.get(PatientDB, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    case_rows = await db.execute(text("SELECT id FROM cases WHERE patient_id = :p"), {"p": patient_id})
    case_ids = [r[0] for r in case_rows.fetchall()]
    total: dict[str, int] = {}
    for cid in case_ids:
        counts = await _cascade_delete_case(db, cid)
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v

    res = await db.execute(text("DELETE FROM patients WHERE id = :p"), {"p": patient_id})
    total["patients"] = res.rowcount or 0
    await db.commit()
    logger.info("Deleted patient %s cascading: %s", patient_id, total)
    return {"patient_id": patient_id, "deleted": total}


def _patient_dict(p: PatientDB) -> dict:
    return {
        "patient_id": p.id,
        "external_id": p.external_id,
        "demographics": p.demographics or {},
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ── Cases ──────────────────────────────────────────────────────────────

@cases_router.post("/cases", status_code=status.HTTP_201_CREATED)
async def create_case(body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    patient = await db.get(PatientDB, body.get("patient_id", ""))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    case = CaseDB(
        id=str(uuid4()),
        patient_id=patient.id,
        tags=body.get("tags", []),
        metadata_json=body.get("metadata", {}),
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return _case_dict(case)


@cases_router.get("/cases")
async def list_cases(
    patient_id: str | None = Query(None, alias="patientId"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CaseDB)
    if patient_id:
        stmt = stmt.where(CaseDB.patient_id == patient_id)
    result = await db.execute(stmt)
    return [_case_dict(c) for c in result.scalars().all()]


@cases_router.get("/cases/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    case = await db.get(CaseDB, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_dict(case)


@cases_router.delete("/cases/{case_id}", status_code=status.HTTP_200_OK)
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Hard-delete a case and all dependent rows (images, results, jobs, artifacts).

    Intended primarily for rollback after a failed upload that left an orphan
    case behind. Use with care.
    """
    case = await db.get(CaseDB, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    counts = await _cascade_delete_case(db, case_id)
    await db.commit()
    logger.info("Deleted case %s cascading: %s", case_id, counts)
    return {"case_id": case_id, "deleted": counts}


@cases_router.patch("/cases/{case_id}")
async def update_case(case_id: str, body: dict[str, Any], db: AsyncSession = Depends(get_db)):
    case = await db.get(CaseDB, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if "status" in body:
        case.status = body["status"]
    if "tags" in body:
        case.tags = body["tags"]
    if "metadata" in body:
        case.metadata_json = body["metadata"]
    await db.commit()
    await db.refresh(case)
    return _case_dict(case)


def _case_dict(c: CaseDB) -> dict:
    return {
        "case_id": c.id,
        "patient_id": c.patient_id,
        "status": c.status,
        "tags": c.tags or [],
        "metadata": c.metadata_json or {},
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
