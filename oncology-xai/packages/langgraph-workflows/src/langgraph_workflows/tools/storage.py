"""Storage tool for LangGraph workflows.

Wraps MinIO/S3 operations for use by LangGraph graph nodes.
Uses boto3 directly (same as oncology_common.storage) or falls back to mock.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "oncology-xai")


class StorageTool:
    """Wrapper around MinIO/S3 for LangGraph workflows."""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self.use_mock:
            return None
        try:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY,
                region_name="us-east-1",
            )
            return self._client
        except ImportError:
            logger.warning("boto3 not available, using mock storage")
            self.use_mock = True
            return None

    def download_file(self, key: str) -> bytes:
        """Download a file from S3/MinIO."""
        if self.use_mock:
            return b"mock_file_data"
        client = self._ensure_client()
        if client is None:
            return b"mock_file_data"
        try:
            resp = client.get_object(Bucket=S3_BUCKET, Key=key)
            return resp["Body"].read()
        except Exception as exc:
            logger.error("Failed to download %s: %s", key, exc)
            raise

    def upload_file(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload data to S3/MinIO and return the URI."""
        if self.use_mock:
            return f"s3://{S3_BUCKET}/{key}"
        client = self._ensure_client()
        if client is None:
            return f"s3://{S3_BUCKET}/{key}"
        try:
            client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=io.BytesIO(data),
                ContentLength=len(data),
                ContentType=content_type,
            )
            return f"s3://{S3_BUCKET}/{key}"
        except Exception as exc:
            logger.error("Failed to upload %s: %s", key, exc)
            raise

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for a file."""
        if self.use_mock:
            return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}?mock_presigned=1"
        client = self._ensure_client()
        if client is None:
            return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}?mock_presigned=1"
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )

    def key_from_uri(self, uri: str) -> str:
        """Extract S3 key from full URI."""
        prefix = f"s3://{S3_BUCKET}/"
        if uri.startswith(prefix):
            return uri[len(prefix):]
        return uri

    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


def get_storage_tool(use_mock: bool | None = None) -> StorageTool:
    """Factory for storage tool."""
    if use_mock is None:
        use_mock = os.getenv("MODEL_BACKEND", "mock") == "mock"
    return StorageTool(use_mock=use_mock)
