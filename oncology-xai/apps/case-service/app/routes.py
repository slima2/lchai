"""Patient and Case CRUD routes."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PatientDB, CaseDB

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
