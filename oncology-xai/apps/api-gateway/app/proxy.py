"""Reverse proxy to downstream services with RBAC."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request, Response

from oncology_common.auth.dependencies import get_current_user, require_roles
from oncology_common.auth.jwt import TokenPayload

logger = logging.getLogger(__name__)

# Route → upstream + required roles
ROUTE_MAP: list[dict[str, Any]] = [
    # Case service (patients, cases CRUD)
    {"prefix": "/patients", "upstream": "case_service_url", "roles": ["clinician", "admin"]},
    {"prefix": "/cases", "upstream": "case_service_url", "roles": ["clinician", "admin"]},
    # Image service
    {"prefix": "/artifacts", "upstream": "image_service_url", "roles": ["clinician", "admin"]},
    {"prefix": "/images", "upstream": "image_service_url", "roles": ["clinician", "admin"]},
    # Inference service
    {"prefix": "/jobs", "upstream": "inference_service_url", "roles": ["clinician", "admin"]},
    {"prefix": "/results", "upstream": "inference_service_url", "roles": ["clinician", "admin"]},
    {"prefix": "/parameters", "upstream": "inference_service_url", "roles": ["clinician", "admin"]},
    {"prefix": "/checkpoints", "upstream": "inference_service_url", "roles": ["clinician", "admin"]},
    # EHR service
    {"prefix": "/ehr", "upstream": "ehr_service_url", "roles": ["clinician", "admin"]},
    # Graph service
    {"prefix": "/graphs", "upstream": "graph_service_url", "roles": ["clinician", "admin"]},
    # Ontology Admin + DeepSearch + KG
    {"prefix": "/admin/ontologies", "upstream": "ontology_admin_service_url", "roles": ["admin"]},
    {"prefix": "/admin/deep-search", "upstream": "ontology_admin_service_url", "roles": ["admin"]},
    {"prefix": "/admin/kg", "upstream": "ontology_admin_service_url", "roles": ["admin"]},
    # Audit
    {"prefix": "/audit", "upstream": "audit_service_url", "roles": ["auditor", "admin"]},
]


def create_proxy_router(settings) -> APIRouter:  # type: ignore[no-untyped-def]
    router = APIRouter()

    async def _proxy(request: Request, upstream_base: str) -> Response:
        """Forward request to upstream, preserving headers."""
        path = request.url.path.replace("/api/v1", "", 1)
        url = f"{upstream_base}/api/v1{path}"
        if request.url.query:
            url += f"?{request.url.query}"

        headers = dict(request.headers)
        headers.pop("host", None)
        cid = getattr(request.state, "correlation_id", None)
        if cid:
            headers["X-Correlation-Id"] = cid

        body = await request.body()
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )

    def _cases_upstream(path: str) -> str:
        """Route /cases/* sub-paths to the correct service."""
        if "/images" in path:
            return settings.image_service_url
        if "/ehr" in path:
            return settings.ehr_service_url
        if "/graph" in path:
            return settings.graph_service_url
        return settings.case_service_url

    def _images_upstream(path: str) -> str:
        """Route /images/* sub-paths: :process and results/latest → inference-service."""
        if ":process" in path or "/results/" in path:
            return settings.inference_service_url
        return settings.image_service_url

    # Register /cases with dynamic upstream (must be before generic loop for /cases)
    @router.api_route(
        "/cases/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_roles("clinician", "admin"))],
        include_in_schema=False,
    )
    async def _cases_handler(request: Request, path: str):
        upstream = _cases_upstream(f"/{path}")
        return await _proxy(request, upstream)

    @router.api_route(
        "/cases",
        methods=["GET", "POST"],
        dependencies=[Depends(require_roles("clinician", "admin"))],
        include_in_schema=False,
    )
    async def _cases_root_handler(request: Request):
        return await _proxy(request, settings.case_service_url)

    # Register /images with dynamic upstream (:process, results/latest → inference-service)
    @router.api_route(
        "/images/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(require_roles("clinician", "admin"))],
        include_in_schema=False,
    )
    async def _images_handler(request: Request, path: str):
        upstream = _images_upstream(f"/{path}")
        return await _proxy(request, upstream)

    @router.api_route(
        "/images",
        methods=["GET", "POST"],
        dependencies=[Depends(require_roles("clinician", "admin"))],
        include_in_schema=False,
    )
    async def _images_root_handler(request: Request):
        return await _proxy(request, settings.image_service_url)

    # Register catch-all routes per prefix (skip /cases and /images - already handled above)
    for route_cfg in ROUTE_MAP:
        prefix = route_cfg["prefix"]
        if prefix in ("/cases", "/images"):
            continue
        upstream_attr = route_cfg["upstream"]
        roles = route_cfg["roles"]

        upstream_url = getattr(settings, upstream_attr)

        @router.api_route(
            f"{prefix}/{{path:path}}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            dependencies=[Depends(require_roles(*roles))],
            include_in_schema=False,
        )
        async def _handler(request: Request, path: str, _url: str = upstream_url):
            return await _proxy(request, _url)

        @router.api_route(
            f"{prefix}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            dependencies=[Depends(require_roles(*roles))],
            include_in_schema=False,
        )
        async def _handler_root(request: Request, _url: str = upstream_url):
            return await _proxy(request, _url)

    return router
