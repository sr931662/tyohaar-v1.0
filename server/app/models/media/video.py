"""
Video — a platform-wide record for every video asset uploaded to Tyohaar.

Covers vendor portfolio videos, booking delivery evidence, celebration memories,
and short-form promotional clips. Supports async transcoding to HLS for adaptive
streaming, thumbnail extraction, and AI-based content moderation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MediaStatus, MediaUsage
from app.models.media.image import ModerationStatus, ImageOwnerType
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class VideoTranscodingStatus(str, enum.Enum):
    """
    Pipeline state of the async video transcoding job.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    NOT_STARTED = "not_started"     # Upload complete; transcoding not yet queued
    QUEUED = "queued"               # Job submitted to the transcoding queue
    PROCESSING = "processing"       # Transcoder is actively processing
    COMPLETED = "completed"         # HLS manifest and segments generated successfully
    FAILED = "failed"               # Transcoding failed; see transcoding_error


class Video(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A single video asset uploaded to and served by the Tyohaar platform.

    Playback strategy:
    - `url` is the original uploaded file (used as fallback and source for transcoding).
    - `streaming_url` is the HLS (.m3u8) manifest URL generated after transcoding.
      This is the URL served to mobile clients for adaptive-bitrate streaming.
    - `thumbnail_url` is a static image extracted at the 10-second mark.
    - `animated_thumbnail_url` is a short GIF/WebP loop for gallery hover previews.

    Transcoding pipeline (async):
    1. Video uploaded → transcoding_status=NOT_STARTED.
    2. Worker picks up job → transcoding_status=QUEUED.
    3. Transcoding begins → transcoding_status=PROCESSING.
    4. Success → streaming_url set, thumbnail_url generated, status=COMPLETED.
    5. Failure → transcoding_status=FAILED, transcoding_error set.

    Moderation:
    - Videos use the same ModerationStatus as images.
    - AI moderation is applied frame-sampling after transcoding completes.
    - Human review is triggered for flagged videos.

    Polymorphic attachment (`entity_type` / `entity_id`) follows the same
    convention as Image — see Image docstring for the full mapping table.

    `extra_metadata` JSONB stores rich video-level data:
        {
          "codec": "h264",
          "audio_codec": "aac",
          "frame_rate": 30,
          "bit_depth": 8,
          "color_space": "yuv420p",
          "ai_labels": ["outdoor", "celebration", "dance"]
        }
    """

    __tablename__ = "videos"

    __table_args__ = (
        Index("ix_videos_owner", "owner_type", "owner_id"),
        Index("ix_videos_entity", "entity_type", "entity_id"),
        Index("ix_videos_usage", "usage"),
        Index("ix_videos_status", "media_status"),
        Index("ix_videos_transcoding_status", "transcoding_status"),
        Index("ix_videos_moderation", "moderation_status"),
        Index("ix_videos_is_featured", "entity_type", "entity_id", "is_featured"),
        CheckConstraint("file_size_bytes > 0", name="ck_videos_file_size_positive"),
        CheckConstraint("duration_seconds > 0", name="ck_videos_duration_positive"),
        CheckConstraint("sort_order >= 0", name="ck_videos_sort_order_non_negative"),
    )

    # ── Storage & Playback URLs ───────────────────────────────────────────────

    url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="CDN URL of the original uploaded video file.",
    )

    streaming_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment=(
            "HLS manifest (.m3u8) URL for adaptive-bitrate streaming. "
            "Populated after transcoding completes."
        ),
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="Static image thumbnail extracted from the video (typically at 10 seconds).",
    )

    animated_thumbnail_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="Short animated WebP/GIF loop for hover previews in galleries.",
    )

    storage_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Canonical cloud object path for the original video file.",
    )

    # ── File Metadata ─────────────────────────────────────────────────────────

    original_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Original filename as provided by the client at upload time.",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Exact file size in bytes of the original uploaded video.",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type e.g. 'video/mp4', 'video/quicktime', 'video/webm'.",
    )

    video_format: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Normalized container format e.g. 'mp4', 'mov', 'webm', 'avi'.",
    )

    # ── Video Properties ──────────────────────────────────────────────────────

    duration_seconds: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        comment="Video duration in seconds. Used for display and storage quotas.",
    )

    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Video width in pixels.",
    )

    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Video height in pixels.",
    )

    bitrate_kbps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Original video bitrate in kilobits per second.",
    )

    # ── Transcoding ───────────────────────────────────────────────────────────

    transcoding_status: Mapped[VideoTranscodingStatus] = mapped_column(
        SAEnum(VideoTranscodingStatus, name="video_transcoding_status", native_enum=False),
        nullable=False,
        default=VideoTranscodingStatus.NOT_STARTED,
    )

    transcoding_job_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="External job ID from the transcoding service (e.g., AWS MediaConvert job ARN).",
    )

    transcoded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the transcoding job completed successfully.",
    )

    transcoding_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from the transcoding service on failure.",
    )

    # ── Context ───────────────────────────────────────────────────────────────

    usage: Mapped[MediaUsage] = mapped_column(
        SAEnum(MediaUsage, name="media_usage", native_enum=False),
        nullable=False,
        comment="Feature context this video belongs to.",
    )

    media_status: Mapped[MediaStatus] = mapped_column(
        SAEnum(MediaStatus, name="media_status", native_enum=False),
        nullable=False,
        default=MediaStatus.UPLOADING,
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the user or vendor who uploaded this video.",
    )

    owner_type: Mapped[ImageOwnerType] = mapped_column(
        SAEnum(ImageOwnerType, name="image_owner_type", native_enum=False),
        nullable=False,
        default=ImageOwnerType.USER,
    )

    # ── Polymorphic Attachment ────────────────────────────────────────────────

    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Domain entity this video is attached to: vendor, booking, memory, etc.",
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the entity this video is attached to.",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for the hero video of the owning entity.",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display ordering within the entity's video collection. Lower = earlier.",
    )

    cdn_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Storage/CDN provider name e.g. 'aws_s3', 'cloudfront', 'cloudinary'.",
    )

    # ── Moderation ────────────────────────────────────────────────────────────

    moderation_status: Mapped[ModerationStatus] = mapped_column(
        SAEnum(ModerationStatus, name="media_moderation_status", native_enum=False),
        nullable=False,
        default=ModerationStatus.PENDING,
    )

    moderation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal reviewer notes or AI flagging reason.",
    )

    moderation_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    moderation_reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who performed the human moderation review.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────

    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the upload completed and the object was persisted to storage.",
    )

    # ── Rich Metadata ─────────────────────────────────────────────────────────

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured video-level data: codec, frame_rate, audio_codec, "
            "bit_depth, AI content labels, scene detection results."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    moderation_reviewer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[moderation_reviewed_by_id],
        lazy="noload",
    )

    @property
    def is_streamable(self) -> bool:
        return (
            self.transcoding_status == VideoTranscodingStatus.COMPLETED
            and self.streaming_url is not None
        )

    @property
    def is_approved(self) -> bool:
        return self.moderation_status == ModerationStatus.APPROVED

    def __repr__(self) -> str:
        return (
            f"<Video id={self.id} usage={self.usage} "
            f"duration={self.duration_seconds}s transcoding={self.transcoding_status}>"
        )
