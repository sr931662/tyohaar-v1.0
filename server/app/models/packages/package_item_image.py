"""
PackageItemImage — photos illustrating a single PackageItem.

Deliberately lighter-weight than PackageGallery (no video/media-type/
status machinery) — package items are simple product-style line items
(e.g. "Balloon Decoration"), not full media assets in their own right.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_item import PackageItem


class PackageItemImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single photo of a PackageItem, shown in a swipeable slider like the package gallery."""

    __tablename__ = "package_item_images"

    __table_args__ = (
        Index("ix_package_item_images_item_id", "item_id"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(String(500), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    item: Mapped[PackageItem] = relationship(
        "PackageItem",
        back_populates="images",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PackageItemImage id={self.id} item_id={self.item_id}>"
