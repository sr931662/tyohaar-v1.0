"""Media domain — service-layer constants."""

from __future__ import annotations

MAX_IMAGE_SIZE_MB = 10
MAX_VIDEO_SIZE_MB = 500
SUPPORTED_IMAGE_FORMATS: set[str] = {"jpg", "jpeg", "png", "webp", "heic"}
SUPPORTED_VIDEO_FORMATS: set[str] = {"mp4", "mov", "avi", "mkv"}
MAX_IMAGES_PER_ENTITY = 50
MAX_VIDEOS_PER_ENTITY = 10
MAX_IMAGES_PER_MEMORY = 30
MAX_VIDEO_DURATION_SECONDS = 600  # 10 minutes
THUMBNAIL_SIZE: tuple[int, int] = (400, 400)
IMAGE_CDN_BASE_URL = ""  # configured via settings

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
