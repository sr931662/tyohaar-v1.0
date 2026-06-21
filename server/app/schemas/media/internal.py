"""Internal/admin media schemas that may include moderation and audit fields."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.schemas.media.common import (
    ImageOwnerType,
    ModerationStatus,
    VideoTranscodingStatus,
    MemoryVisibility,
)
from app.models.enums import MediaUsage, MediaStatus


class ImageInternal(BaseSchema):
    """Full image record for admin/moderation use — includes moderation_status."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    owner_type: ImageOwnerType
    owner_id: uuid.UUID
    url: str
    thumbnail_url: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    usage: MediaUsage
    status: MediaStatus
    moderation_status: ModerationStatus  # INTERNAL — admin/moderation only
    alt_text: str | None = None
    display_order: int
    is_primary: bool
    deleted_at: datetime | None = None  # INTERNAL — soft-delete
    created_at: datetime
    updated_at: datetime


class VideoInternal(BaseSchema):
    """Full video record for admin/transcoding pipeline use."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    owner_type: ImageOwnerType
    owner_id: uuid.UUID
    url: str
    thumbnail_url: str | None = None
    processed_url: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    usage: MediaUsage
    status: MediaStatus
    transcoding_status: VideoTranscodingStatus
    title: str | None = None
    description: str | None = None
    is_primary: bool
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MemoryInternal(BaseSchema):
    """Full memory record for admin use — includes share_token."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    celebration_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    visibility: MemoryVisibility
    share_token: str | None = None  # INTERNAL — do not expose in public responses
    memory_date: str | None = None
    location: str | None = None
    image_ids: list[str] | None = None
    video_ids: list[str] | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MediaModerationUpdate(BaseSchema):
    """Admin action to approve or reject an image/video."""

    moderation_status: ModerationStatus
    rejection_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Required when moderation_status is REJECTED",
    )

    def model_post_init(self, __context: object) -> None:
        if self.moderation_status == ModerationStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting media")
