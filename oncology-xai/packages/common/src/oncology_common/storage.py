"""MinIO / S3 storage helpers."""

from __future__ import annotations

import hashlib
import logging
from typing import BinaryIO

import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)


class StorageClient:
    """S3-compatible object storage client wrapping MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        kwargs: dict = {
            "region_name": region,
            "config": Config(signature_version="s3v4"),
        }
        # Use explicit credentials for MinIO (local), IAM role for AWS S3 (EKS)
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        if endpoint and "amazonaws.com" not in endpoint:
            kwargs["endpoint_url"] = endpoint
        self._client = boto3.client("s3", **kwargs)

    # ── upload ──────────────────────────────────────────────────────────
    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes. Returns the S3 URI."""
        sha = hashlib.sha256(data).hexdigest()
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": sha},
        )
        return f"s3://{self.bucket}/{key}"

    def upload_fileobj(self, key: str, fobj: BinaryIO, content_type: str = "application/octet-stream") -> str:
        self._client.upload_fileobj(fobj, self.bucket, key, ExtraArgs={"ContentType": content_type})
        return f"s3://{self.bucket}/{key}"

    # ── download ────────────────────────────────────────────────────────
    def download_bytes(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    # ── presigned URL ───────────────────────────────────────────────────
    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    # ── hash ────────────────────────────────────────────────────────────
    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
