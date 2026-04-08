"""
Trigger re-analysis of a slide via the inference-service API.

After delta training, this module calls the existing inference pipeline
to regenerate overlays, pattern composition, and mutation predictions
using the updated model. The inference-service is never modified.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

POLL_INTERVAL = 3.0
POLL_TIMEOUT = 600.0


async def trigger_reanalysis(image_id: str, case_id: str) -> dict:
    """Call inference-service to re-process a slide.

    Returns the job status dict with result_bundle_id on success.
    """
    base = settings.inference_service_url
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(
            f"{base}/api/v1/images/{image_id}:process",
            json={"case_id": case_id, "use_choquet": True},
        )
        resp.raise_for_status()
        job = resp.json()
        job_id = job["job_id"]
        logger.info("Triggered re-analysis: job_id=%s, image_id=%s", job_id, image_id)

        start = time.monotonic()
        while time.monotonic() - start < POLL_TIMEOUT:
            poll = await client.get(f"{base}/api/v1/jobs/{job_id}")
            poll.raise_for_status()
            data = poll.json()
            status = data.get("status", "UNKNOWN")

            if status == "COMPLETED":
                logger.info("Re-analysis completed: rb=%s", data.get("result_bundle_id"))
                return data
            elif status == "FAILED":
                logger.error("Re-analysis failed: %s", data.get("error_detail"))
                return data

            await _sleep(POLL_INTERVAL)

        return {"status": "TIMEOUT", "error_detail": f"Timed out after {POLL_TIMEOUT}s"}


async def _sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)
