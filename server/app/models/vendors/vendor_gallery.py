"""
VendorGalleryItem — media assets in a vendor's portfolio gallery.
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
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MediaStatus, MediaType, MediaUsage
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor
    from app.models.vendors.vendor_service import VendorService


class VendorGalleryItem(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A single image or video in a vendor's portfolio gallery.

    Gallery items can be associated with the vendor as a whole or scoped
    to a specific service. `is_featured` items are surfaced prominently
    in matching results and internal briefing materials.

    Soft-deletion is used so orphaned CDN assets can be cleaned up
    asynchronously before hard-deletion.
    """

    __tablename__ = "vendor_gallery_items"

    __table_args__ = (
        Index("ix_vendor_gallery_vendor_id", "vendor_id"),
        Index("ix_vendor_gallery_service_id", "service_id"),
        Index("ix_vendor_gallery_featured", "vendor_id", "is_featured", "status"),
        Index("ix_vendor_gallery_sort_order", "vendor_id", "sort_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_services.id", ondelete="SET NULL"),
        nullable=True,
        comment="Scopes this gallery item to a specific service. NULL = applies to vendor overall.",
    )

    # ── Media Asset ───────────────────────────────────────────────────────────

    media_type: Mapped[MediaType] = mapped_column(
        SAEnum(MediaType, name="media_type", native_enum=False),
        nullable=False,
    )

    usage: Mapped[MediaUsage] = mapped_column(
        SAEnum(MediaUsage, name="media_usage", native_enum=False),
        nullable=False,
        default=MediaUsage.VENDOR_GALLERY,
    )

    file_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment="CDN URL of the full-resolution media file",
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the compressed/resized thumbnail",
    )

    # ── Media Metadata ────────────────────────────────────────────────────────

    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    width_px: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Image width in pixels (images only)",
    )

    height_px: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Image height in pixels (images only)",
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Video duration in seconds (videos only)",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Ascending sort order within this vendor's gallery",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Featured items are shown first in matching and internal briefing views",
    )

    status: Mapped[MediaStatus] = mapped_column(
        SAEnum(MediaStatus, name="media_status", native_enum=False),
        nullable=False,
        default=MediaStatus.ACTIVE,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="gallery")

    service: Mapped[VendorService | None] = relationship("VendorService", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<VendorGalleryItem id={self.id} vendor_id={self.vendor_id} "
            f"type={self.media_type} featured={self.is_featured}>"
        )
