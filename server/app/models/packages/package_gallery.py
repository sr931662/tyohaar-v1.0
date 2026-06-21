"""
PackageGallery — media assets (photos/videos) showcasing a package.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MediaStatus, MediaType, MediaUsage
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageGallery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A photo or video asset associated with a package.

    Gallery items are shown to customers on the package detail page.
    `is_featured` marks the primary image used in cards and search results.
    `sort_order` controls display sequence within the gallery.
    """

    __tablename__ = "package_gallery_items"

    __table_args__ = (
        Index("ix_package_gallery_package_id", "package_id"),
        Index("ix_package_gallery_featured", "package_id", "is_featured", "sort_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Media ─────────────────────────────────────────────────────────────────

    media_type: Mapped[MediaType] = mapped_column(
        SAEnum(MediaType, name="media_type", native_enum=False),
        nullable=False,
    )

    usage: Mapped[MediaUsage] = mapped_column(
        SAEnum(MediaUsage, name="media_usage", native_enum=False),
        nullable=False,
    )

    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="CDN URL for the full-resolution file",
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="CDN URL for the compressed thumbnail",
    )

    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)

    alt_text: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Accessibility alt text for screen readers",
    )

    # ── Video Metadata ────────────────────────────────────────────────────────

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Video duration in seconds. NULL for images.",
    )

    # ── Image Metadata ────────────────────────────────────────────────────────

    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Display ───────────────────────────────────────────────────────────────

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="The featured item is used as the package card cover image",
    )

    status: Mapped[MediaStatus] = mapped_column(
        SAEnum(MediaStatus, name="media_status", native_enum=False),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="gallery",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageGallery id={self.id} package_id={self.package_id} "
            f"type={self.media_type} featured={self.is_featured}>"
        )
