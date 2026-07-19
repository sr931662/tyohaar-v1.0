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
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package
    from app.models.packages.package_item_image import PackageItemImage
    from app.models.packages.package_item_vendor import PackageItemVendor
    from app.models.vendors.vendor_category import VendorCategory


# Join table attaching a common (vendor-owned, reusable) PackageItem to one
# or more packages, without duplicating the item row. Package-specific items
# never use this table — they keep the direct package_id FK on PackageItem.
package_item_links = Table(
    "package_item_links",
    Base.metadata,
    Column(
        "package_id",
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "package_item_id",
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


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
        Index("ix_package_items_vendor_id", "vendor_id"),
        CheckConstraint(
            "(is_common AND package_id IS NULL) OR (NOT is_common AND package_id IS NOT NULL)",
            name="ck_package_items_common_xor_package",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    # NULL for common items (which live outside any single package and are
    # attached to N packages via package_item_links); required for
    # package-specific items, which keep the direct one-to-many shape.
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Set only for common items — the vendor who owns this reusable item
    # template. NULL for package-specific items (ownership is inherited
    # from the parent Package.vendor_id instead).
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_common: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for a vendor-owned reusable item template attached to "
                "packages via package_item_links; False for a normal "
                "package-specific item.",
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

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Default/minimum quantity included in the package template.",
    )

    max_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Highest quantity a customer may select for this item at booking "
                "time (e.g. cap balloon bunches at 20). NULL means uncapped — the "
                "customer can request any quantity >= `quantity`.",
    )

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

    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Item's cover/thumbnail image, shown on item rows and as the "
                "first slide of its gallery (mirrors Package.cover_image_url)",
    )

    # ── Vendor Logistics ──────────────────────────────────────────────────────

    prep_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Vendor-suggested setup/prep time (minutes) required before the "
                "event's scheduled start. Copied onto BookingItem at booking time.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package | None] = relationship(
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

    images: Mapped[list[PackageItemImage]] = relationship(
        "PackageItemImage",
        back_populates="item",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    # Packages this common item is attached to (empty for package-specific
    # items, which use package_id directly instead of this join table).
    linked_packages: Mapped[list[Package]] = relationship(
        "Package",
        secondary=package_item_links,
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageItem id={self.id} name={self.name!r} "
            f"mandatory={self.is_mandatory}>"
        )
