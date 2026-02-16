"""RabbitMQ event publisher."""

from __future__ import annotations

import json
import logging

import pika

from event_contracts.envelope import EventEnvelope

logger = logging.getLogger(__name__)

EXCHANGE = "oncology.events"


class EventPublisher:
    """Publish EventEnvelope messages to RabbitMQ topic exchange."""

    def __init__(self, rabbitmq_url: str, exchange: str = EXCHANGE):
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange

    def publish(self, envelope: EventEnvelope, routing_key: str | None = None) -> None:
        rk = routing_key or envelope.event_type
        try:
            conn = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            ch = conn.channel()
            ch.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
            ch.basic_publish(
                exchange=self.exchange,
                routing_key=rk,
                body=envelope.model_dump_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            conn.close()
            logger.info("Published %s → %s", envelope.event_type, rk)
        except Exception:
            logger.exception("Failed to publish event %s", envelope.event_id)
