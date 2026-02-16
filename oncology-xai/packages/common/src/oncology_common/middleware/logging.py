"""Structured logging middleware (no PHI)."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("oncology.access")


def configure_logging(service_name: str, level: str = "INFO") -> None:
    """Configure structured logging."""
    fmt = f"%(asctime)s [{service_name}] %(levelname)s %(name)s — %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response without PHI."""

    def __init__(self, app, service_name: str = "service"):  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        correlation_id = getattr(request.state, "correlation_id", "-")
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.1fms corr=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            correlation_id,
        )
        return response
