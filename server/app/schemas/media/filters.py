"""Filter/query-parameter schemas for media domain list endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.media.common import (
    ImageOwnerType,
    ModerationStatus,
    VideoTranscodingStatus,
    MemoryVisibility,
)
from app.models.enums import MediaUsage, MediaStatus


class ImageFilters(BaseSchema):
    """Query parameters for listing images."""

    owner_type: ImageOwnerType | None = None
    owner_id: uuid.UUID | None = None
    usage: MediaUsage | None = None
    status: MediaStatus | None = None
    is_primary: bool | None = None
    moderation_status: ModerationStatus | None = Field(
        default=None,
        description="Admin-only filter — include only for internal/admin endpoints",
    )


class VideoFilters(BaseSchema):
    """Query parameters for listing videos."""

    owner_type: ImageOwnerType | None = None
    owner_id: uuid.UUID | None = None
    usage: MediaUsage | None = None
    status: MediaStatus | None = None
    transcoding_status: VideoTranscodingStatus | None = None


class MemoryFilters(BaseSchema):
    """Query parameters for listing memories."""

    user_id: uuid.UUID | None = None
    celebration_id: uuid.UUID | None = None
    visibility: MemoryVisibility | None = None
    from_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter memory_date >= from_date (YYYY-MM-DD)",
    )
    to_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter memory_date <= to_date (YYYY-MM-DD)",
    )
