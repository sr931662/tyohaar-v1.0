"""Media domain — stateless helper functions."""

from __future__ import annotations

import uuid


def validate_file_extension(filename: str, allowed: set[str]) -> bool:
    """Return True if the file's extension (lowercased) is in *allowed*."""
    ext = get_file_extension(filename)
    return ext in allowed


def get_file_extension(filename: str) -> str:
    """Return the lowercased extension without the leading dot.

    Returns an empty string if the filename has no extension.
    """
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def generate_storage_key(owner_id: uuid.UUID, entity_type: str, filename: str) -> str:
    """Build a deterministic, collision-resistant cloud storage key.

    Pattern: media/{owner_id}/{entity_type}/{random_uuid}/{filename}
    """
    segment = uuid.uuid4()
    return f"media/{owner_id}/{entity_type}/{segment}/{filename}"


def build_public_url(storage_key: str, cdn_base: str) -> str:
    """Construct the public CDN URL from a storage key and base URL.

    If cdn_base is empty the storage_key is returned unchanged (dev mode).
    """
    if not cdn_base:
        return storage_key
    base = cdn_base.rstrip("/")
    key = storage_key.lstrip("/")
    return f"{base}/{key}"


def estimate_transcoding_time(file_size_mb: float) -> int:
    """Rough estimate of transcoding time in seconds.

    Rule of thumb: ~1 second per MB, minimum 30 seconds.
    """
    return max(30, int(file_size_mb))
