"""Standard event envelope (DERCAS 5.1)."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Immutable event envelope sent over RabbitMQ."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:16]}")
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid4().hex[:16]}")
    producer: str
    case_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
