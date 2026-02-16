"""Inference Service — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from oncology_common.middleware.correlation import CorrelationMiddleware
from oncology_common.middleware.logging import LoggingMiddleware, configure_logging
from oncology_common.observability.tracing import setup_tracing, instrument_fastapi
from oncology_common.observability.metrics import setup_metrics, MetricsMiddleware
from oncology_common.models.base import HealthResponse, ErrorResponse

from app.config import settings
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    if settings.otel_exporter_otlp_endpoint:
        setup_tracing(settings.service_name, settings.otel_exporter_otlp_endpoint)
    yield


app = FastAPI(
    title="LCHAI Inference Service",
    description="ML pipeline: CTransPath + FuzzyArcLoss v3 SubCenters + SHAP",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware, service_name=settings.service_name)
app.add_middleware(CorrelationMiddleware)
setup_metrics(app)
instrument_fastapi(app)
app.include_router(router)


@app.exception_handler(Exception)
async def _exc(request: Request, exc: Exception):
    cid = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(errorCode="INTERNAL_ERROR", message="Unexpected error", correlationId=cid).model_dump(by_alias=True),
    )


@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(status="healthy", service=settings.service_name, version=settings.version)
