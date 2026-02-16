"""Audit query routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditEventDB

router = APIRouter(prefix="/api/v1", tags=["Audit"])


@router.get("/audit/events")
async def list_events(
    case_id: str | None = Query(None, alias="caseId"),
    event_type: str | None = Query(None, alias="type"),
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditEventDB).order_by(AuditEventDB.timestamp.desc()).limit(limit)
    if case_id:
        stmt = stmt.where(AuditEventDB.case_id == case_id)
    if event_type:
        stmt = stmt.where(AuditEventDB.event_type == event_type)
    result = await db.execute(stmt)
    return [_evt(e) for e in result.scalars().all()]


@router.get("/audit/events/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEventDB).where(AuditEventDB.event_id == event_id))
    evt = result.scalar_one_or_none()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    return _evt(evt)


def _evt(e: AuditEventDB) -> dict:
    return {
        "event_id": e.event_id,
        "event_type": e.event_type,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "correlation_id": e.correlation_id,
        "user_id": e.user_id,
        "case_id": e.case_id,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "action": e.action,
        "status": e.status,
        "details": e.details or {},
    }
