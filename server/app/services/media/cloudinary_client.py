"""
Cloudinary-backed image storage client.

Configuration is lazy so the app can boot without credentials — uploads
simply fail with a clear ExternalServiceError until CLOUDINARY_* env vars
are set (see app/core/config.py).
"""

from __future__ import annotations

import cloudinary
import cloudinary.api
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
    except Exception:
        if apply_watermark:
            # The watermark overlay asset likely hasn't been uploaded to
            # Cloudinary yet (or the transform otherwise failed) — degrade to
            # a plain upload instead of blocking every image upload on it.
            # Not narrowed to a specific error message: Cloudinary's wording
            # for a missing overlay resource varies, and any watermark-step
            # failure should fall back rather than 500 the whole upload.
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


async def destroy_asset(public_id: str, *, resource_type: str = "image") -> bool:
    """Delete one Cloudinary object and confirm it is gone.

    Unlike `delete_image`, this reports its outcome rather than swallowing it,
    because the deletion pipeline is not permitted to claim success for an
    object that still exists.

    Returns True when the object was deleted or was already absent — both mean
    "not there any more", which is what makes this idempotent. Returns False
    when Cloudinary reported anything else; the caller records the asset as
    unresolved rather than dropping the row that points at it.

    `invalidate=True` purges CDN copies as well as the origin object. Without
    it a deleted image stays served from edge caches for its remaining TTL.

    Configuration failure is reported the same way as any other failure —
    False, never an exception. An earlier version called `_ensure_configured()`
    outside the try, so an unconfigured deployment raised instead: the purge
    handler died mid-transaction, its `unresolved_media_assets` bookkeeping was
    rolled back with it, and the next handler then saw no blockers and deleted
    the very rows that were the only pointers to the surviving objects. The
    guarantee has to hold hardest exactly when storage is misconfigured.
    """

    def _destroy() -> dict:
        _ensure_configured()
        return cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True,
        )

    try:
        response = await run_in_threadpool(_destroy)
    except Exception:  # noqa: BLE001 - any failure means "still there"
        return False

    # Cloudinary returns {"result": "ok"} on delete and {"result": "not found"}
    # when the object is already gone. Both are acceptable end states.
    return response.get("result") in {"ok", "not found"}


def parse_public_id(url: str) -> str | None:
    """Recover a Cloudinary public_id from a delivery URL.

    Used only by the one-off backfill for media uploaded before the id was
    persisted. Deliberately conservative: it returns None rather than a guess,
    because a wrong id deletes someone else's asset or silently deletes
    nothing while reporting success.

    Handles the standard shape:
        https://res.cloudinary.com/<cloud>/<type>/upload/<transforms>/v123/<folder>/<name>.<ext>
    """
    if "res.cloudinary.com" not in url and "/upload/" not in url:
        return None

    try:
        _, after_upload = url.split("/upload/", 1)
    except ValueError:
        return None

    segments = [s for s in after_upload.split("/") if s]
    if not segments:
        return None

    # Drop leading transformation segments (they contain '_' pairs like
    # 'w_300,h_300') and the version segment ('v1699887766').
    while segments and (
        segments[0].startswith("v")
        and segments[0][1:].isdigit()
        or ("," in segments[0] and "_" in segments[0])
    ):
        segments.pop(0)

    if not segments:
        return None

    public_id = "/".join(segments)
    # Strip the format extension, but only a real one — folder names may
    # legitimately contain dots.
    if "." in public_id.rsplit("/", 1)[-1]:
        public_id = public_id.rsplit(".", 1)[0]

    return public_id or None


async def asset_exists(public_id: str, *, resource_type: str = "image") -> bool:
    """Confirm a public_id actually resolves to an object we own.

    The backfill uses this to verify a parsed id before persisting it, so a
    mis-parse is caught at backfill time rather than at purge time when the
    consequence is a false "deleted" claim.
    """
    _ensure_configured()

    def _fetch() -> dict:
        return cloudinary.api.resource(public_id, resource_type=resource_type)

    try:
        await run_in_threadpool(_fetch)
    except Exception:  # noqa: BLE001 - not found, or not ours
        return False
    return True
