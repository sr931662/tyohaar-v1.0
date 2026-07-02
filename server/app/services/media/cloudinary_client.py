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


async def upload_image_bytes(file_bytes: bytes, folder: str) -> dict:
    """Upload raw image bytes to Cloudinary and return its response dict."""
    _ensure_configured()

    def _upload() -> dict:
        return cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="image")

    return await run_in_threadpool(_upload)


def delete_image(public_id: str) -> None:
    """Best-effort delete of a Cloudinary asset by its public_id."""
    _ensure_configured()
    cloudinary.uploader.destroy(public_id, resource_type="image")
