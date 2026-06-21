"""
Media domain — shared types and local enum definitions.

The media models define several local enums that are not in app.models.enums
because they are tightly coupled to individual model files. We define them
here as Python (str, enum.Enum) classes so schema consumers do not need to
import from ORM model files directly.

Import pattern for schemas and service layer:
    from app.schemas.media.common import ImageOwnerType, ModerationStatus, ...
"""

from __future__ import annotations

import enum

from app.models.enums import MediaStatus, MediaType, MediaUsage

__all__ = [
    # local enums (not in app.models.enums)
    "ImageOwnerType",
    "ModerationStatus",
    "VideoTranscodingStatus",
    "MemoryVisibility",
    # re-exports from app.models.enums
    "MediaType",
    "MediaUsage",
    "MediaStatus",
]


class ImageOwnerType(str, enum.Enum):
    """
    Discriminator for the polymorphic owner of an Image record.

    Mirrors the local enum defined in app.models.media.image (ImageOwnerType).
    """

    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"


class ModerationStatus(str, enum.Enum):
    """
    Content moderation pipeline state for uploaded images.

    PENDING: awaiting automated and/or manual review.
    APPROVED: cleared for public display.
    REJECTED: violates content policy; hidden from all views.
    REQUIRES_REVIEW: flagged by automation; pending human decision.

    Mirrors the local enum in app.models.media.image.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


class VideoTranscodingStatus(str, enum.Enum):
    """
    State of the asynchronous video transcoding pipeline.

    NOT_STARTED: video uploaded but not yet queued.
    QUEUED: job submitted to the transcoding worker.
    IN_PROGRESS: transcoding is running.
    COMPLETED: processed_url is available for playback.
    FAILED: transcoding failed; see Video.status for full state.

    Mirrors the local enum in app.models.media.video.
    """

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MemoryVisibility(str, enum.Enum):
    """
    Visibility scope for a user's Memory album.

    PRIVATE: only the owner can view.
    SHARED_LINK: accessible via a share_token URL (no login required).
    PUBLIC: listed in public discovery if the platform enables it.

    Mirrors the local enum in app.models.media.memory.
    """

    PRIVATE = "private"
    SHARED_LINK = "shared_link"
    PUBLIC = "public"
