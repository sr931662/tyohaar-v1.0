"""Media domain — service-layer exceptions."""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class ImageNotFoundError(NotFoundError):
    def __init__(self, image_id: str | None = None) -> None:
        super().__init__("Image", image_id)


class ImageOwnershipError(PermissionError):
    default_message = "You do not own this image."


class VideoNotFoundError(NotFoundError):
    def __init__(self, video_id: str | None = None) -> None:
        super().__init__("Video", video_id)


class VideoOwnershipError(PermissionError):
    default_message = "You do not own this video."


class MemoryNotFoundError(NotFoundError):
    def __init__(self, memory_id: str | None = None) -> None:
        super().__init__("Memory", memory_id)


class MemoryOwnershipError(PermissionError):
    default_message = "You do not own this memory album."


class MemoryAccessDeniedError(PermissionError):
    default_message = "This memory album is private."


class UnsupportedFileFormatError(ValidationError):
    def __init__(self, ext: str, allowed: set[str]) -> None:
        super().__init__(
            f"File format '{ext}' is not supported. Allowed: {sorted(allowed)}",
            field="file_format",
        )


class FileSizeLimitError(BusinessRuleError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(f"File exceeds the maximum allowed size of {max_mb} MB.")


class ImageCountLimitError(BusinessRuleError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Entity has reached the maximum of {limit} images.")


class ModerationRejectedError(BusinessRuleError):
    default_message = "This media item has been rejected by moderation."
