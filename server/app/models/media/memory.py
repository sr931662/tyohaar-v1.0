"""
Memory — a curated media album capturing moments from a customer's celebration.

Customers create Memory albums to collect and organise images and videos from
their celebrations. Albums can be kept private, shared via a unique link, or
made publicly visible on the Tyohaar platform as portfolio-quality content.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration
    from app.models.users.user import User


class MemoryVisibility(str, enum.Enum):
    """
    Controls who can see a Memory album.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PRIVATE = "private"         # Visible only to the album owner
    SHARED_LINK = "shared_link" # Visible to anyone with the shared_token URL
    PUBLIC = "public"           # Listed on the platform; indexed by search


class Memory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A curated media album for a celebration's moments.

    A Memory groups Image and Video records (attached via entity_type='memory',
    entity_id=Memory.id) into a themed album for a specific celebration.

    One celebration can have multiple Memory albums (e.g., Pre-Wedding, Main
    Ceremony, Reception) but typically one primary album is created by the platform
    when a booking is completed.

    Visibility model:
    - PRIVATE:      owner-only; default after creation.
    - SHARED_LINK:  anyone with the `share_url` (derived from `shared_token`) can view.
    - PUBLIC:       listed in the platform's public memory/portfolio feed.

    `shared_token` is a URL-safe random string generated when the owner first
    enables sharing. It remains stable and can be revoked by generating a new one.

    Media counts (`image_count`, `video_count`) are denormalized for feed
    performance and kept in sync by the service layer on every media add/remove.

    `cover_image_id` points to the Image record used as the album thumbnail.
    It can be any Image attached to this Memory (entity_id=this.id).

    `event_date` is denormalized from Celebration.event_date for fast sorting
    and filtering of memory feeds without joining celebrations.

    `extra_metadata` JSONB stores unstructured album attributes:
        {
          "occasion_type": "wedding",
          "vendor_names": ["Studio XYZ", "Decorator ABC"],
          "highlight_reel_url": "https://cdn.tyohaar.com/...",
          "ai_tags": ["outdoor", "floral", "traditional"]
        }
    """

    __tablename__ = "memories"

    __table_args__ = (
        UniqueConstraint("shared_token", name="uq_memories_shared_token"),
        Index("ix_memories_celebration_id", "celebration_id"),
        Index("ix_memories_customer_id", "customer_id"),
        Index("ix_memories_visibility", "visibility"),
        Index("ix_memories_is_featured", "is_featured"),
        Index("ix_memories_event_date", "event_date"),
        Index("ix_memories_public_feed", "visibility", "is_featured", "event_date"),
        CheckConstraint("image_count >= 0", name="ck_memories_image_count_non_negative"),
        CheckConstraint("video_count >= 0", name="ck_memories_video_count_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The celebration these memories are from.",
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer who owns this Memory album.",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Album title e.g. 'Priya & Arjun's Wedding Reception'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional customer-written caption or description for the album.",
    )

    # ── Cover ─────────────────────────────────────────────────────────────────

    cover_image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the Image record used as the album thumbnail. "
            "Must be an Image with entity_type='memory' and entity_id=this.id. "
            "Not a FK to avoid circular dependencies."
        ),
    )

    # ── Visibility ────────────────────────────────────────────────────────────

    visibility: Mapped[MemoryVisibility] = mapped_column(
        SAEnum(MemoryVisibility, name="memory_visibility", native_enum=False),
        nullable=False,
        default=MemoryVisibility.PRIVATE,
    )

    shared_token: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment=(
            "URL-safe random token for generating the shared link. "
            "Set when visibility first changes to SHARED_LINK or PUBLIC."
        ),
    )

    shared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the owner first enabled sharing for this album.",
    )

    # ── Media Counts (denormalized) ───────────────────────────────────────────

    image_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of active Image records with entity_type='memory', entity_id=this.id.",
    )

    video_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of active Video records with entity_type='memory', entity_id=this.id.",
    )

    # ── Featured ──────────────────────────────────────────────────────────────

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for albums curated for the platform's public memory feed. "
            "Only PLATFORM admins should set this; customer-set flag has no effect."
        ),
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the owner has archived the album. Hidden from feeds but not deleted.",
    )

    # ── Date Context ──────────────────────────────────────────────────────────

    event_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment=(
            "Date of the celebration event. Denormalized from Celebration for "
            "fast memory-feed sorting without joining celebrations."
        ),
    )

    # ── Tags & Metadata ───────────────────────────────────────────────────────

    tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Customer or AI-generated searchable tags e.g. ['wedding', 'outdoor', 'night'].",
    )

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Unstructured album attributes: occasion_type, vendor_names, "
            "highlight_reel_url, AI scene tags, A/B test context."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        lazy="noload",
    )

    customer: Mapped[User] = relationship(
        "User",
        lazy="noload",
    )

    @property
    def total_media_count(self) -> int:
        return self.image_count + self.video_count

    @property
    def share_url_token(self) -> str | None:
        return self.shared_token

    def __repr__(self) -> str:
        return (
            f"<Memory id={self.id} title={self.title!r} "
            f"visibility={self.visibility} media={self.total_media_count}>"
        )
