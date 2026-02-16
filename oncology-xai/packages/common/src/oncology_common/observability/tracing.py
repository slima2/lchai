"""OpenTelemetry tracing setup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_tracing(service_name: str, otlp_endpoint: str) -> None:
    """Configure OTel TracerProvider with OTLP exporter."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OTel tracing configured → %s", otlp_endpoint)
    except Exception as exc:
        logger.warning("OTel tracing setup failed: %s", exc)


def instrument_fastapi(app: "FastAPI") -> None:
    """Instrument FastAPI with OTel."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:
        logger.warning("FastAPI OTel instrumentation failed: %s", exc)
