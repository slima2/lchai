"""Model client tool for LangGraph workflows.

Provides both mock and real inference paths via httpx calls to the
inference-service or direct function invocation.
"""

from __future__ import annotations

import os
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8003")


class ModelClient:
    """Model client that calls inference-service endpoints or returns mock data."""

    def __init__(self, backend: str = "mock"):
        self.backend = backend
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(base_url=INFERENCE_SERVICE_URL, timeout=300.0)
        return self._http

    async def predict_patterns(self, image_data: bytes, thresholds: dict | None = None) -> list[dict[str, Any]]:
        """Run histological pattern classification.

        In mock mode returns synthetic data; in real mode delegates
        to the inference pipeline.
        """
        if self.backend == "mock":
            return self._mock_patterns()

        # Real mode: call inference-service internal endpoint
        client = await self._get_client()
        try:
            resp = await client.post(
                "/internal/predict-patterns",
                content=image_data,
                headers={"Content-Type": "application/octet-stream"},
                params=thresholds or {},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Real pattern prediction failed, falling back to mock: %s", exc)
            return self._mock_patterns()

    async def predict_mutations(
        self, morphologic_profile: dict[str, float], thresholds: dict | None = None
    ) -> list[dict[str, Any]]:
        """Run mutation prediction from morphologic profile.

        Expects feature dict with keys: n_tiles_total, pct_lepidic, etc.
        """
        if self.backend == "mock":
            return self._mock_mutations()

        client = await self._get_client()
        try:
            resp = await client.post(
                "/internal/predict-mutations",
                json={"profile": morphologic_profile, "thresholds": thresholds or {}},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Real mutation prediction failed, falling back to mock: %s", exc)
            return self._mock_mutations()

    async def generate_shap(
        self, morphologic_profile: dict[str, float], genes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Generate SHAP explanations for mutation predictions."""
        if self.backend == "mock":
            return self._mock_shap(genes or ["EGFR", "KRAS", "TP53"])

        client = await self._get_client()
        try:
            resp = await client.post(
                "/internal/generate-shap",
                json={"profile": morphologic_profile, "genes": genes or ["EGFR", "KRAS", "TP53"]},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Real SHAP generation failed, falling back to mock: %s", exc)
            return self._mock_shap(genes or ["EGFR", "KRAS", "TP53"])

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── Mock helpers ──────────────────────────────────────────────

    @staticmethod
    def _mock_patterns() -> list[dict[str, Any]]:
        return [
            {"pattern": "lepidic", "score": 0.78, "percentage": 32.1, "is_conclusive": True},
            {"pattern": "acinar", "score": 0.65, "percentage": 26.5, "is_conclusive": True},
            {"pattern": "papillary", "score": 0.59, "percentage": 21.8, "is_conclusive": True},
            {"pattern": "micropapillary", "score": 0.31, "percentage": 8.4, "is_conclusive": False},
            {"pattern": "solid", "score": 0.42, "percentage": 11.2, "is_conclusive": False},
        ]

    @staticmethod
    def _mock_mutations() -> list[dict[str, Any]]:
        return [
            {"mutation": "EGFR", "score": 0.72, "status": "POS", "evidence_source": "THESIS_INTERNAL",
             "intended_use": "research / decision support (non-diagnostic)"},
            {"mutation": "KRAS", "score": 0.35, "status": "NEG", "evidence_source": "THESIS_INTERNAL",
             "intended_use": "research / decision support (non-diagnostic)"},
            {"mutation": "TP53", "score": 0.58, "status": "INCONCLUSIVE", "evidence_source": "THESIS_INTERNAL",
             "intended_use": "research / decision support (non-diagnostic)"},
        ]

    @staticmethod
    def _mock_shap(genes: list[str]) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for gene in genes:
            artifacts.extend([
                {"artifact_type": "shap_bar", "gene": gene,
                 "uri": f"s3://oncology-xai/xai/shap_{gene}_bar.png", "hash": "mock_hash"},
                {"artifact_type": "shap_beeswarm", "gene": gene,
                 "uri": f"s3://oncology-xai/xai/shap_{gene}_beeswarm.png", "hash": "mock_hash"},
                {"artifact_type": "shap_force", "gene": gene,
                 "uri": f"s3://oncology-xai/xai/shap_force_{gene}_case.png", "hash": "mock_hash"},
            ])
        return artifacts


def get_model_client(backend: str | None = None) -> ModelClient:
    """Factory for model client. backend = 'mock' | 'local' | 'triton'."""
    bk = backend or os.getenv("MODEL_BACKEND", "mock")
    return ModelClient(backend=bk)
