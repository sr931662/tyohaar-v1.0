"""
Cloudinary-backed image storage client.

Configuration is lazy so the app can boot without credentials — uploads
simply fail with a clear ExternalServiceError until CLOUDINARY_* env vars
are set (see app/core/config.py).
"""

from __future__ import annotations

import cloudinary
import cloudinary.uploader
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.exceptions import ExternalServiceError

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        raise ExternalServiceError(
            "Cloudinary",
            "Image upload is not configured yet. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.",
        )
    if not _configured:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        _configured = True


def _watermark_transformation() -> list[dict]:
    """
    Subtle bottom-right logo overlay applied to every package/vendor/occasion/
    banner image so a saved/downloaded copy is never watermark-free. Requires
    the Tyohaar logo to be uploaded to Cloudinary at CLOUDINARY_WATERMARK_PUBLIC_ID
    (see app/core/config.py) — upload_image_bytes() falls back to a plain
    upload if that asset doesn't exist yet, so this never blocks uploads.
    """
    watermark_id = settings.CLOUDINARY_WATERMARK_PUBLIC_ID.replace("/", ":")
    return [
        {
            "overlay": watermark_id,
            "gravity": "south_east",
            "x": 16,
            "y": 16,
            "width": 0.14,
            "flags": "relative",
            "opacity": 55,
        },
        {"flags": "layer_apply"},
    ]


async def upload_image_bytes(
    file_bytes: bytes,
    folder: str,
    resource_type: str = "image",
    apply_watermark: bool = True,
) -> dict:
    """
    Upload raw file bytes to Cloudinary and return its response dict.

    apply_watermark bakes the Tyohaar logo into the stored image itself (not
    just a client-side overlay) — set False for profile photos (handled by
    upload_profile_photo_bytes instead), support attachments, and vendor KYC
    documents, none of which should carry a marketing watermark.
    """
    _ensure_configured()

    def _upload(with_watermark: bool) -> dict:
        kwargs: dict = {"folder": folder, "resource_type": resource_type}
        if with_watermark and resource_type == "image":
            kwargs["transformation"] = _watermark_transformation()
        return cloudinary.uploader.upload(file_bytes, **kwargs)

    try:
        return await run_in_threadpool(_upload, apply_watermark)
    except Exception as exc:
        if apply_watermark and "overlay" in str(exc).lower():
            # Watermark logo hasn't been uploaded to Cloudinary yet — degrade
            # to a plain upload instead of blocking every image upload on it.
            return await run_in_threadpool(_upload, False)
        raise


async def upload_profile_photo_bytes(file_bytes: bytes, folder: str) -> dict:
    """
    Upload a profile photo with a face-aware square crop baked in.

    Unlike upload_image_bytes(), the stored "display" version is already
    cropped to a 400x400 face-centered square with auto format/quality — the
    generic path stores full-resolution originals as-is, which is fine for
    package/vendor galleries but meant tiny avatar circles were fetching
    large uncropped originals (slow on weak networks, and poorly centered).
    """
    _ensure_configured()

    def _upload() -> dict:
        return cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type="image",
            transformation=[{
                "width": 400,
                "height": 400,
                "crop": "fill",
                "gravity": "face",
                "quality": "auto",
                "fetch_format": "auto",
            }],
        )

    return await run_in_threadpool(_upload)


def delete_image(public_id: str) -> None:
    """Best-effort delete of a Cloudinary asset by its public_id."""
    _ensure_configured()
    cloudinary.uploader.destroy(public_id, resource_type="image")
