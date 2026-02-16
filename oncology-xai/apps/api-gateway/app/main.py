"""API Gateway — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oncology_common.auth.jwt import JWTValidator
from oncology_common.middleware.correlation import CorrelationMiddleware
from oncology_common.middleware.logging import LoggingMiddleware, configure_logging
from oncology_common.observability.tracing import setup_tracing, instrument_fastapi
from oncology_common.observability.metrics import setup_metrics, MetricsMiddleware
from oncology_common.models.base import HealthResponse, ErrorResponse

from app.config import settings
from app.proxy import create_proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    if settings.otel_exporter_otlp_endpoint:
        setup_tracing(settings.service_name, settings.otel_exporter_otlp_endpoint)
    app.state.jwt_validator = JWTValidator(jwks_url=settings.jwks_url)
    yield


app = FastAPI(
    title="LCHAI API Gateway",
    description="Oncology XAI API Gateway — JWT/RBAC proxy",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware, service_name=settings.service_name)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_metrics(app)
instrument_fastapi(app)

# Proxy routes
app.include_router(create_proxy_router(settings), prefix="/api/v1")


@app.exception_handler(Exception)
async def _exc(request: Request, exc: Exception):
    cid = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            errorCode="INTERNAL_ERROR", message="Unexpected error", correlationId=cid
        ).model_dump(by_alias=True),
    )


@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(status="healthy", service=settings.service_name, version=settings.version)


@app.get("/auth/me", tags=["Auth"])
async def auth_me(request: Request):
    """Return current user from JWT (for testing)."""
    from oncology_common.auth.dependencies import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(request, creds)
        return {"user_id": user.user_id, "roles": user.roles, "email": user.email, "name": user.name}
    return JSONResponse(status_code=401, content={"detail": "Missing token"})
