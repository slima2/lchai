"""Image upload / viewer routes."""

from __future__ import annotations

import hashlib
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from oncology_common.storage import StorageClient
from app.config import settings
from app.database import get_db
from app.models import ImageDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Images"])


def _storage() -> StorageClient:
    return StorageClient(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )


@router.post("/cases/{case_id}/images:upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    case_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload histopathological image. Supported: png, jpg, jpeg, tif, tiff, svs, bif, biff."""
    data = await file.read()
    ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower()
    allowed = ("png", "jpg", "jpeg", "tif", "tiff", "svs", "bif", "biff")
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Supported: {', '.join(allowed)}")

    checksum = hashlib.sha256(data).hexdigest()
    image_id = str(uuid4())
    key = f"images/{case_id}/{image_id}.{ext}"

    storage = _storage()
    uri = storage.upload_bytes(key, data, content_type=file.content_type or "image/png")

    img = ImageDB(
        id=image_id,
        case_id=case_id,
        format=ext,
        storage_uri=uri,
        checksum=checksum,
        size_bytes=len(data),
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)
    return _img_dict(img)


@router.get("/cases/{case_id}/images")
async def list_images(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImageDB).where(ImageDB.case_id == case_id))
    return [_img_dict(i) for i in result.scalars().all()]


@router.get("/images/{image_id}")
async def get_image(image_id: str, db: AsyncSession = Depends(get_db)):
    img = await db.get(ImageDB, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return _img_dict(img)


@router.get("/images/{image_id}/viewer-url")
async def get_viewer_url(image_id: str, db: AsyncSession = Depends(get_db)):
    img = await db.get(ImageDB, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    storage = _storage()
    key = img.storage_uri.replace(f"s3://{settings.s3_bucket}/", "")
    url = storage.presigned_url(key, expires_in=3600)
    return {"image_id": image_id, "viewer_url": url}


@router.get("/artifacts/presigned")
async def get_artifact_presigned(key: str = Query(...)):
    """Return artifact bytes from MinIO (proxy). Used by frontend <img> tags."""
    storage = _storage()
    try:
        data = storage.download_bytes(key)
    except Exception as exc:
        logger.error("Failed to download artifact key=%s: %s", key, exc)
        raise HTTPException(status_code=404, detail=f"Artifact not found: {key}")

    # Determine content type from key extension
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else "bin"
    ct_map = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "tif": "image/tiff", "tiff": "image/tiff", "svs": "application/octet-stream",
        "svg": "image/svg+xml", "json": "application/json",
        "html": "text/html", "csv": "text/csv",
    }
    content_type = ct_map.get(ext, "application/octet-stream")
    return Response(content=data, media_type=content_type)


def _img_dict(img: ImageDB) -> dict:
    return {
        "image_id": img.id,
        "case_id": img.case_id,
        "format": img.format,
        "storage_uri": img.storage_uri,
        "checksum": img.checksum,
        "size_bytes": img.size_bytes,
        "stain": img.stain,
        "magnification": img.magnification,
        "notes": img.notes,
        "uploaded_by": img.uploaded_by,
        "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else None,
    }
