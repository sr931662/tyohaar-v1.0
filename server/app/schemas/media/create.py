"""
Media domain — create (input) schemas.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.models.enums import MediaUsage
from app.schemas.base import BaseSchema
from app.schemas.media.common import (
    ImageOwnerType,
    MemoryVisibility,
    VideoTranscodingStatus,
)

__all__ = [
    "ImageCreate",
    "VideoCreate",
    "MemoryCreate",
]

# Shared MIME type validator
_ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/avif",
}
_ALLOWED_VIDEO_MIMES = {
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
}


class ImageCreate(BaseSchema):
    """
    Input schema for registering a newly uploaded image with the platform.

    The actual file upload is handled separately by the storage service.
    This schema records the resulting CDN URL and metadata.
    """

    owner_type: ImageOwnerType = Field(
        description="Discriminator for the owning entity type: USER, VENDOR, or ADMIN.",
    )
    owner_id: uuid.UUID = Field(description="UUID of the owning entity.")
    url: str = Field(
        max_length=2048,
        description="CDN URL of the full-size image.",
    )
    thumbnail_url: str | None = Field(
        default=None,
        max_length=2048,
        description="CDN URL of the generated thumbnail (populated after processing).",
    )
    file_name: str | None = Field(
        default=None,
        max_length=300,
        description="Original filename as uploaded by the client.",
    )
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        le=20 * 1024 * 1024,  # 20 MB max
        description="File size in bytes. Must not exceed 20 MB.",
    )
    width: int | None = Field(default=None, ge=1, description="Image width in pixels.")
    height: int | None = Field(default=None, ge=1, description="Image height in pixels.")
    mime_type: str | None = Field(
        default=None,
        max_length=100,
        description="MIME type, e.g. 'image/jpeg'. Must be an allowed image type.",
    )
    usage: MediaUsage = Field(
        description="Feature context this image belongs to (e.g. PROFILE_PHOTO).",
    )
    alt_text: str | None = Field(
        default=None,
        max_length=500,
        description="Accessibility alt text for screen readers.",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Ascending sort order within the owner's gallery.",
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is the primary/featured image for the owner.",
    )

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_IMAGE_MIMES:
            raise ValueError(
                f"mime_type '{v}' is not allowed. Accepted types: {_ALLOWED_IMAGE_MIMES}"
            )
        return v


class VideoCreate(BaseSchema):
    """
    Input schema for registering a newly uploaded video.

    processed_url and transcoding_status are set by the transcoding pipeline
    after upload. At creation time, transcoding_status defaults to NOT_STARTED.
    """

    owner_type: ImageOwnerType = Field(
        description="Discriminator for the owning entity type.",
    )
    owner_id: uuid.UUID = Field(description="UUID of the owning entity.")
    url: str = Field(
        max_length=2048,
        description="Storage URL of the raw uploaded video.",
    )
    thumbnail_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Thumbnail extracted from the video (populated after transcoding).",
    )
    file_name: str | None = Field(default=None, max_length=300)
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        le=500 * 1024 * 1024,  # 500 MB max
        description="File size in bytes. Must not exceed 500 MB.",
    )
    duration_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Video duration in seconds (populated after processing).",
    )
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    mime_type: str | None = Field(default=None, max_length=100)
    usage: MediaUsage
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    is_primary: bool = Field(default=False)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_VIDEO_MIMES:
            raise ValueError(
                f"mime_type '{v}' is not allowed. Accepted types: {_ALLOWED_VIDEO_MIMES}"
            )
        return v


# Aliases consumed by the media controller
ImageUploadRegisterCreate = ImageCreate
VideoUploadRegisterCreate = VideoCreate


class MemoryCreate(BaseSchema):
    """
    Input schema for creating a new Memory album.

    image_ids and video_ids reference existing Image and Video UUIDs
    owned by the user. The service layer validates ownership before linking.
    """

    user_id: uuid.UUID = Field(description="Owner of this memory album.")
    celebration_id: uuid.UUID | None = Field(
        default=None,
        description="Optionally links this memory to a specific Celebration.",
    )
    title: str = Field(
        max_length=300,
        min_length=1,
        description="Album title, e.g. 'Rahul's 30th Birthday Party'.",
    )
    description: str | None = Field(
        default=None,
        description="Optional longer description of the memory.",
    )
    visibility: MemoryVisibility = Field(
        default=MemoryVisibility.PRIVATE,
        description="Who can view this memory album.",
    )
    memory_date: date | None = Field(
        default=None,
        description="Date the memory was created/occurred (not the upload date).",
    )
    location: str | None = Field(
        default=None,
        max_length=300,
        description="Location name or address where the memory took place.",
    )
    image_ids: list[str] | None = Field(
        default=None,
        description="UUIDs (as strings) of Image records to include in this memory.",
    )
    video_ids: list[str] | None = Field(
        default=None,
        description="UUIDs (as strings) of Video records to include in this memory.",
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Memory title must not be blank.")
        return v.strip()
