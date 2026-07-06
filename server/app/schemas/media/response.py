"""Response schemas for the media domain — safe for public API responses."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.schemas.media.common import (
    ImageOwnerType,
    ModerationStatus,
    VideoTranscodingStatus,
    MemoryVisibility,
)
from app.models.enums import MediaUsage, MediaStatus


class ImageResponse(BaseSchema):
    """Public image record response. moderation_status is excluded (internal)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    owner_type: ImageOwnerType
    owner_id: uuid.UUID
    url: str
    thumbnail_url: str | None = None
    file_name: str | None = Field(default=None, validation_alias="original_filename")
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    usage: MediaUsage
    status: MediaStatus = Field(validation_alias="media_status")
    alt_text: str | None = None
    display_order: int = Field(default=0, validation_alias="sort_order")
    is_primary: bool = Field(default=False, validation_alias="is_featured")
    created_at: datetime
    updated_at: datetime


class VideoResponse(BaseSchema):
    """Public video record response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    owner_type: ImageOwnerType
    owner_id: uuid.UUID
    url: str
    thumbnail_url: str | None = None
    processed_url: str | None = None
    file_name: str | None = Field(default=None, validation_alias="original_filename")
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    usage: MediaUsage
    status: MediaStatus = Field(validation_alias="media_status")
    transcoding_status: VideoTranscodingStatus = VideoTranscodingStatus.NOT_STARTED
    title: str | None = None
    description: str | None = None
    is_primary: bool = Field(default=False, validation_alias="is_featured")
    created_at: datetime
    updated_at: datetime


class MemoryResponse(BaseSchema):
    """
    Public memory response.
    share_token is intentionally excluded — only returned via the dedicated
    share endpoint to prevent accidental token leakage.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID = Field(validation_alias="customer_id")
    celebration_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    visibility: MemoryVisibility
    memory_date: date | None = Field(default=None, validation_alias="event_date")
    location: str | None = None
    image_ids: list[str] | None = None
    video_ids: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class MemoryShareResponse(BaseSchema):
    """
    Returned only when a user explicitly generates a share link.
    Contains the share_token — do NOT embed in list responses.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    visibility: MemoryVisibility
    share_token: str = Field(description="Opaque token for shared-link access. Treat as a secret.")
    share_url: str | None = Field(default=None, description="Constructed by the service layer")
