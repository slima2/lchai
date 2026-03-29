"""RabbitMQ consumer that persists audit events."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from event_contracts.envelope import EventEnvelope
from event_contracts.consumer import BaseConsumer
from app.config import settings
from app.models import AuditEventDB

logger = logging.getLogger(__name__)


def _persist_event(envelope: EventEnvelope) -> None:
    """Persist audit event to DB (idempotent by event_id)."""
    engine = create_engine(settings.postgres_dsn_sync)
    with Session(engine) as session:
        existing = session.query(AuditEventDB).filter_by(event_id=envelope.event_id).first()
        if existing:
            logger.debug("Duplicate event_id=%s, skipping", envelope.event_id)
            return

        evt = AuditEventDB(
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            timestamp=envelope.timestamp,
            correlation_id=envelope.correlation_id,
            user_id=envelope.payload.get("user_id"),
            case_id=envelope.case_id,
            entity_type=envelope.payload.get("entity_type", "unknown"),
            entity_id=envelope.payload.get("entity_id", "unknown"),
            action=envelope.payload.get("action", envelope.event_type),
            status=envelope.payload.get("status", "SUCCESS"),
            details=envelope.payload,
        )
        session.add(evt)
        session.commit()
        logger.info("Persisted audit event %s", envelope.event_id)


def start_consumer() -> None:
    """Start blocking audit consumer."""
    consumer = BaseConsumer(
        rabbitmq_url=settings.rabbitmq_url,
        queue_name="audit-events",
    )
    consumer.on("#", _persist_event)  # listen to all events
    consumer.start(binding_keys=["#"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_consumer()
