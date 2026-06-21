"""
Image — a platform-wide record for every image asset uploaded to Tyohaar.

Covers all image contexts: vendor galleries, booking evidence, invitation cards,
celebration memories, user profile photos, package thumbnails, and CMS banners.
Designed for CDN-backed storage with deduplication, AI moderation, and lazy
transcoding into WebP compressed variants.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MediaStatus, MediaUsage
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class ModerationStatus(str, enum.Enum):
    """
    Content moderation pipeline state for an image or video asset.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"             # Awaiting moderation review (auto or manual)
    APPROVED = "approved"           # Safe for public display
    REQUIRES_REVIEW = "requires_review"  # Flagged by AI; awaiting human review
    REJECTED = "rejected"           # Removed due to policy violation


class ImageOwnerType(str, enum.Enum):
    """
    Type of entity that owns (uploaded) this image.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    USER = "user"
    VENDOR = "vendor"
    SYSTEM = "system"           # Platform-uploaded assets (banners, defaults)
    ADMIN = "admin"


class Image(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A single image asset uploaded to and served by the Tyohaar platform.

    Every image is stored once (keyed by `content_hash` for deduplication)
    and referenced by multiple entities via the polymorphic `entity_type` +
    `entity_id` attachment fields.

    Storage:
    - `storage_path` is the canonical cloud object path (S3/GCS key).
    - `url` is the CDN-accelerated public URL derived from storage_path.
    - `thumbnail_url` is a 300×300 max webp thumbnail generated on upload.
    - `compressed_url` is a quality-reduced WebP version (≤85% of original size).

    Moderation:
    - All user-uploaded images start with moderation_status=PENDING.
    - System images and admin-uploaded images are auto-approved.
    - AI vision API runs asynchronously; flags transition to REQUIRES_REVIEW.
    - Human review transitions to APPROVED or REJECTED.
    - Rejected images are soft-deleted (deleted_at set) and their CDN URLs purged.

    Deduplication:
    - `content_hash` (SHA-256 of raw bytes) prevents storing identical files twice.
    - The service layer checks for an existing active Image with the same hash
      before inserting a new row.

    `extra_metadata` JSONB stores rich image-level data:
        {
          "exif": {taken_at, gps_lat, gps_lng, camera_model},
          "colors": ["#FF5722", "#4CAF50"],   // dominant color palette
          "ai_labels": ["party", "outdoor", "family"],
          "blur_score": 0.12
        }

    Polymorphic attachment (`entity_type` / `entity_id`) links the image to its
    primary display context:
        "vendor"      → vendors.id
        "booking"     → bookings.id
        "celebration" → celebrations.id
        "invitation"  → invitations.id
        "memory"      → memories.id
        "package"     → packages.id
        "user"        → users.id
        "occasion"    → occasions.id
    """

    __tablename__ = "images"

    __table_args__ = (
        Index("ix_images_owner", "owner_type", "owner_id"),
        Index("ix_images_entity", "entity_type", "entity_id"),
        Index("ix_images_usage", "usage"),
        Index("ix_images_status", "media_status"),
        Index("ix_images_moderation", "moderation_status"),
        Index("ix_images_content_hash", "content_hash"),
        Index("ix_images_is_featured", "entity_type", "entity_id", "is_featured"),
        CheckConstraint("file_size_bytes > 0", name="ck_images_file_size_positive"),
        CheckConstraint("width > 0", name="ck_images_width_positive"),
        CheckConstraint("height > 0", name="ck_images_height_positive"),
        CheckConstraint("sort_order >= 0", name="ck_images_sort_order_non_negative"),
    )

    # ── Storage ───────────────────────────────────────────────────────────────

    url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="CDN-accelerated public URL for the full-resolution image.",
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="CDN URL of the 300×300 WebP thumbnail. Generated asynchronously after upload.",
    )

    compressed_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="CDN URL of the quality-reduced WebP variant. Used for feed cards and previews.",
    )

    storage_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Canonical cloud object path (S3 key or GCS object name).",
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
        comment="Exact file size in bytes of the original uploaded image.",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type e.g. 'image/jpeg', 'image/png', 'image/webp', 'image/gif'.",
    )

    image_format: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Normalized format string e.g. 'jpeg', 'png', 'webp', 'gif', 'heic'.",
    )

    # ── Dimensions ────────────────────────────────────────────────────────────

    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Image width in pixels.",
    )

    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Image height in pixels.",
    )

    # ── Accessibility ─────────────────────────────────────────────────────────

    alt_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Accessibility alternative text. May be auto-generated by AI vision.",
    )

    # ── Context ───────────────────────────────────────────────────────────────

    usage: Mapped[MediaUsage] = mapped_column(
        SAEnum(MediaUsage, name="media_usage", native_enum=False),
        nullable=False,
        comment="Feature context this image belongs to.",
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
        comment=(
            "UUID of the user or vendor who uploaded this image. "
            "Not a FK to allow vendor owner references without a FK constraint."
        ),
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
        comment="Table/domain this image is attached to: vendor, booking, memory, user, etc.",
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the entity this image is attached to. "
            "Not a FK to support cross-domain attachment without join constraints."
        ),
    )

    # ── Display ───────────────────────────────────────────────────────────────

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for the primary/cover image of the owning entity.",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display ordering within the entity's image gallery. Lower = earlier.",
    )

    # ── Deduplication ─────────────────────────────────────────────────────────

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hex digest of raw image bytes. Used to detect duplicate uploads.",
    )

    cdn_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Storage/CDN provider name e.g. 'aws_s3', 'gcs', 'cloudinary'.",
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
        comment="Reason for rejection or human reviewer notes. Internal only.",
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
            "Structured image-level data: EXIF fields, AI labels, dominant colors, "
            "blur score, face detection results. Internal only."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    moderation_reviewer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[moderation_reviewed_by_id],
        lazy="noload",
    )

    @property
    def aspect_ratio(self) -> float | None:
        if self.width and self.height:
            return round(self.width / self.height, 4)
        return None

    @property
    def is_approved(self) -> bool:
        return self.moderation_status == ModerationStatus.APPROVED

    def __repr__(self) -> str:
        return (
            f"<Image id={self.id} usage={self.usage} "
            f"{self.width}x{self.height} status={self.media_status}>"
        )
