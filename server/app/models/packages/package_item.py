"""
PackageItem — a service component within a package.

Each package consists of items (Decoration, Photography, Cake, etc.).
The vendor assigned to deliver each item is tracked in PackageItemVendor (internal).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package
    from app.models.packages.package_item_vendor import PackageItemVendor
    from app.models.vendors.vendor_category import VendorCategory


class PackageItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single deliverable service line within a package.

    Examples in a "Birthday Starter Pack":
    - 1× Balloon Decoration (mandatory)
    - 1× Birthday Cake 1kg (mandatory)
    - 1× Photography 2 Hours (optional)

    `category_id` links to VendorCategory (Decoration, Photography, etc.)
    for service type classification and internal admin operations.

    The vendor(s) who will deliver this item are stored in `PackageItemVendor`
    (internal). Never expose PackageItemVendor data to customers.
    """

    __tablename__ = "package_items"

    __table_args__ = (
        Index("ix_package_items_package_id", "package_id"),
        Index("ix_package_items_category_id", "category_id"),
        Index("ix_package_items_display_order", "package_id", "display_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Service Classification ────────────────────────────────────────────────

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Links to VendorCategory for service type taxonomy (Decoration, Photography, etc.)",
    )

    # ── Item Details ──────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of quantity (e.g. 'hours', 'kg', 'pieces', 'persons')",
    )

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Price of this item line within the package.",
    )

    # ── Flags ─────────────────────────────────────────────────────────────────

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Mandatory items are always included; optional items can be toggled off",
    )

    is_customizable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if the customer can configure options for this item (flavor, color, etc.)",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="items",
        lazy="noload",
    )

    category: Mapped[VendorCategory | None] = relationship(
        "VendorCategory",
        lazy="noload",
    )

    vendor_assignments: Mapped[list[PackageItemVendor]] = relationship(
        "PackageItemVendor",
        back_populates="package_item",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageItem id={self.id} name={self.name!r} "
            f"mandatory={self.is_mandatory}>"
        )
