"""Image upload / viewer routes."""

from __future__ import annotations

import hashlib
import io
import logging
from uuid import uuid4

import numpy as np
from PIL import Image as PILImage
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import Request
from oncology_common.storage import StorageClient
from event_contracts.envelope import EventEnvelope
from event_contracts.publisher import EventPublisher
from app.config import settings
from app.database import get_db
from app.models import ImageDB

logger = logging.getLogger(__name__)


def _publish_audit(event_type: str, case_id: str, image_id: str, user: str, details: dict | None = None) -> None:
    """Fire-and-forget audit event to RabbitMQ."""
    try:
        pub = EventPublisher(settings.rabbitmq_url)
        pub.publish(EventEnvelope(
            event_type=event_type,
            producer="image-service",
            case_id=case_id,
            payload={"image_id": image_id, "user_id": user, "action": "UPLOAD", "entity_type": "image", "entity_id": image_id, **(details or {})},
        ))
    except Exception:
        logger.warning("Failed to publish audit event %s", event_type, exc_info=True)


def _validate_he_stain(data: bytes, ext: str) -> None:
    """Reject images that are not H&E stained. LCHAI was trained exclusively on H&E.

    Analyzes a thumbnail of the image to detect non-H&E color profiles:
    - IHC/DAB (brown chromogen)
    - Alcian Blue, PAS, trichrome (non-pink/purple dominant)
    - Immunofluorescence (very dark with bright spots)
    """
    try:
        if ext in ("svs", "bif", "biff"):
            try:
                import openslide
                import tempfile, os
                suffix = {"svs": ".svs", "bif": ".bif", "biff": ".bif"}.get(ext, ".tif")
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    f.write(data[:min(len(data), 100_000_000)])
                    tmp = f.name
                try:
                    slide = openslide.OpenSlide(tmp)
                    thumb = slide.get_thumbnail((512, 512))
                    slide.close()
                finally:
                    os.unlink(tmp)
                arr = np.array(thumb.convert("RGB"))
            except Exception:
                return
        else:
            img = PILImage.open(io.BytesIO(data))
            img.thumbnail((512, 512))
            arr = np.array(img.convert("RGB"))

        r_mean = float(arr[:, :, 0].mean())
        g_mean = float(arr[:, :, 1].mean())
        b_mean = float(arr[:, :, 2].mean())
        brightness = (r_mean + g_mean + b_mean) / 3

        # H&E tissue: pink (R dominant) or purple (R~B, both > G)
        # Background is white/near-white, tissue is pink/purple
        # Non-H&E indicators:
        is_blue_dominant = b_mean > r_mean + 15 and b_mean > g_mean + 15 and r_mean < 160
        is_brown_dominant = r_mean > 150 and g_mean > 100 and b_mean < 90 and (r_mean - b_mean) > 60
        is_very_dark = brightness < 60
        is_green_dominant = g_mean > r_mean + 10 and g_mean > b_mean + 10

        reasons = []
        if is_blue_dominant:
            reasons.append("blue-dominant stain detected (possible Alcian Blue, trichrome, or special stain)")
        if is_brown_dominant:
            reasons.append("brown chromogen detected (possible IHC/DAB stain)")
        if is_very_dark and not is_brown_dominant:
            reasons.append("very dark image (possible immunofluorescence or unstained)")
        if is_green_dominant:
            reasons.append("green-dominant image (not compatible with H&E)")

        if reasons:
            detail = (
                f"NON-H&E IMAGE REJECTED: {'; '.join(reasons)}. "
                f"Color profile: R={r_mean:.0f} G={g_mean:.0f} B={b_mean:.0f}. "
                f"LCHAI v2.0 was trained exclusively on H&E-stained slides. "
                f"Please upload an H&E-stained image."
            )
            logger.warning("Upload rejected: %s", detail)
            raise HTTPException(status_code=422, detail=detail)

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("H&E validation skipped (could not analyze thumbnail): %s", e)


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
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload histopathological image. Supported: png, jpg, jpeg, tif, tiff, svs, bif, biff."""
    uploaded_by = request.headers.get("x-user-id", "unknown")
    data = await file.read()
    ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower()
    allowed = ("png", "jpg", "jpeg", "tif", "tiff", "svs", "bif", "biff")
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Supported: {', '.join(allowed)}")

    # Validate H&E staining color profile (reject IHC, special stains)
    _validate_he_stain(data, ext)

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
        uploaded_by=uploaded_by,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)
    _publish_audit("image.uploaded", case_id, image_id, uploaded_by, {"filename": file.filename, "size_bytes": len(data)})
    return _img_dict(img)


ALLOWED_EXTENSIONS = ("png", "jpg", "jpeg", "tif", "tiff", "svs", "bif", "biff")

CT_MAP = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "tif": "image/tiff", "tiff": "image/tiff", "svs": "application/octet-stream",
    "bif": "application/octet-stream", "biff": "application/octet-stream",
}


MULTIPART_THRESHOLD = 4_500_000_000  # 4.5 GB — use multipart for files above this
PART_SIZE = 100_000_000  # 100 MB per part


@router.post("/cases/{case_id}/images:request-upload", status_code=status.HTTP_200_OK)
async def request_upload(case_id: str, body: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Return presigned URL(s) for direct S3 upload.

    For files < 4.5 GB: returns a single presigned PUT URL.
    For files >= 4.5 GB: returns multipart upload URLs (one per 100 MB part).

    Body: { "filename": "slide.svs", "size_bytes": 10000000000 }
    """
    filename = body.get("filename", "image.png")
    size_bytes = body.get("size_bytes", 0)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    image_id = str(uuid4())
    key = f"images/{case_id}/{image_id}.{ext}"
    content_type = CT_MAP.get(ext, "application/octet-stream")
    storage = _storage()
    uploaded_by = request.headers.get("x-user-id", "unknown")

    response: dict = {
        "image_id": image_id,
        "s3_key": key,
        "content_type": content_type,
    }

    def _externalize(url: str) -> str:
        """Replace internal Docker hostname with browser-accessible endpoint."""
        ext_ep = settings.s3_endpoint_external
        if ext_ep and ext_ep != settings.s3_endpoint:
            return url.replace(settings.s3_endpoint, ext_ep, 1)
        return url

    if size_bytes >= MULTIPART_THRESHOLD:
        upload_id = storage.create_multipart_upload(key, content_type=content_type)
        num_parts = max(1, -(-size_bytes // PART_SIZE))  # ceil division
        part_urls = []
        for i in range(1, num_parts + 1):
            url = storage.presigned_upload_part(key, upload_id, i, expires_in=7200)
            part_urls.append({"part_number": i, "presigned_url": _externalize(url)})
        response["multipart"] = True
        response["upload_id"] = upload_id
        response["part_size"] = PART_SIZE
        response["part_urls"] = part_urls
    else:
        presigned_url = storage.presigned_put_url(key, content_type=content_type, expires_in=7200)
        response["multipart"] = False
        response["presigned_url"] = _externalize(presigned_url)

    img = ImageDB(
        id=image_id,
        case_id=case_id,
        format=ext,
        storage_uri=f"s3://{settings.s3_bucket}/{key}",
        checksum="pending-upload",
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)

    return response


@router.post("/cases/{case_id}/images:complete-multipart", status_code=status.HTTP_200_OK)
async def complete_multipart(case_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Complete a multipart upload after all parts have been uploaded.

    Body: { "image_id": "uuid", "upload_id": "...", "parts": [{"ETag": "...", "PartNumber": 1}, ...] }
    """
    image_id = body.get("image_id")
    upload_id = body.get("upload_id")
    parts = body.get("parts", [])

    if not image_id or not upload_id or not parts:
        raise HTTPException(status_code=400, detail="image_id, upload_id, and parts are required")

    img = await db.get(ImageDB, image_id)
    if not img or img.case_id != case_id:
        raise HTTPException(status_code=404, detail="Image not found")

    storage = _storage()
    key = img.storage_uri.replace(f"s3://{settings.s3_bucket}/", "")

    try:
        storage.complete_multipart_upload(key, upload_id, parts)
    except Exception as exc:
        logger.error("Failed to complete multipart upload for %s: %s", key, exc)
        raise HTTPException(status_code=400, detail=f"Failed to complete multipart upload: {exc}")

    try:
        head = storage.head_object(key)
        img.size_bytes = head.get("ContentLength", 0)
        img.checksum = (head.get("ETag") or "").strip('"')
    except Exception as exc:
        logger.error("S3 head_object failed for %s: %s", key, exc)

    await db.commit()
    await db.refresh(img)
    _publish_audit("image.uploaded", case_id, image_id, img.uploaded_by or "unknown", {"size_bytes": img.size_bytes})
    return _img_dict(img)


@router.post("/cases/{case_id}/images:confirm-upload", status_code=status.HTTP_200_OK)
async def confirm_upload(case_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Confirm that a presigned upload completed. Verifies the object exists in S3.

    Body: { "image_id": "uuid" }
    """
    image_id = body.get("image_id")
    if not image_id:
        raise HTTPException(status_code=400, detail="image_id is required")

    img = await db.get(ImageDB, image_id)
    if not img or img.case_id != case_id:
        raise HTTPException(status_code=404, detail="Image not found")

    storage = _storage()
    key = img.storage_uri.replace(f"s3://{settings.s3_bucket}/", "")

    try:
        head = storage.head_object(key)
        actual_size = head.get("ContentLength", 0)
        img.size_bytes = actual_size
        img.checksum = (head.get("ETag") or "").strip('"')
    except Exception as exc:
        logger.error("S3 head_object failed for %s: %s", key, exc)
        raise HTTPException(status_code=400, detail="Upload not found in storage. Did the upload complete?")

    await db.commit()
    await db.refresh(img)
    _publish_audit("image.uploaded", case_id, image_id, img.uploaded_by or "unknown", {"size_bytes": actual_size})
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

    ext = key.rsplit(".", 1)[-1].lower() if "." in key else "bin"
    ct_map = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "tif": "image/tiff", "tiff": "image/tiff", "svs": "application/octet-stream",
        "svg": "image/svg+xml", "json": "application/json",
        "html": "text/html", "csv": "text/csv",
    }
    content_type = ct_map.get(ext, "application/octet-stream")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


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
