"""Base RabbitMQ consumer."""

from __future__ import annotations

import json
import logging
from typing import Callable

import pika

from event_contracts.envelope import EventEnvelope

logger = logging.getLogger(__name__)

EXCHANGE = "oncology.events"


class BaseConsumer:
    """Subscribe to RabbitMQ topics and dispatch handlers."""

    def __init__(self, rabbitmq_url: str, queue_name: str, exchange: str = EXCHANGE):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.exchange = exchange
        self._handlers: dict[str, Callable] = {}

    def on(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def start(self, binding_keys: list[str] | None = None) -> None:
        """Blocking consume loop."""
        conn = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        ch = conn.channel()
        ch.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        ch.queue_declare(queue=self.queue_name, durable=True)

        for key in binding_keys or ["#"]:
            ch.queue_bind(exchange=self.exchange, queue=self.queue_name, routing_key=key)

        def _callback(ch, method, properties, body):  # type: ignore[no-untyped-def]
            try:
                envelope = EventEnvelope.model_validate_json(body)
                handler = self._handlers.get(envelope.event_type)
                if handler:
                    handler(envelope)
                else:
                    logger.debug("No handler for %s", envelope.event_type)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                logger.exception("Error processing message")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        ch.basic_qos(prefetch_count=10)
        ch.basic_consume(queue=self.queue_name, on_message_callback=_callback)
        logger.info("Consuming from %s", self.queue_name)
        ch.start_consuming()
