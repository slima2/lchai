"""Prometheus metrics helpers."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from fastapi import FastAPI


def setup_metrics(app: "FastAPI") -> None:
    """Mount /metrics endpoint."""
    try:
        from prometheus_client import make_asgi_app

        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    except Exception:
        pass


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request latency and count."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        try:
            from prometheus_client import Histogram

            REQUEST_LATENCY = Histogram(
                "http_request_duration_seconds",
                "Request latency",
                ["method", "path", "status"],
            )
            elapsed = time.perf_counter() - start
            REQUEST_LATENCY.labels(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
            ).observe(elapsed)
        except Exception:
            pass
        return response
