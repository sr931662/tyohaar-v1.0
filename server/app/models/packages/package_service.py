"""
PackageServiceLine — a labor/service component within a package.

Named PackageServiceLine (not PackageService) to avoid colliding with the
package-domain business-logic class `PackageService` in
app.services.packages.service.

Mirrors PackageItem exactly (see package_item.py) but for services the
vendor performs (Photography, DJ, Makeup, etc.) rather than physical
items. Two deliberate differences from PackageItem: no `is_returnable`
(doesn't apply to a service) and no reviews/likes (engagement features
scoped to tangible items, not services).
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
    from app.models.packages.package_service_image import PackageServiceImage
    from app.models.vendors.vendor_category import VendorCategory


# Join table attaching a common (vendor-owned, reusable) PackageServiceLine to
# one or more packages, without duplicating the service row. Package-specific
# services never use this table — they keep the direct package_id FK on
# PackageServiceLine.
package_service_links = Table(
    "package_service_links",
    Base.metadata,
    Column(
        "package_id",
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "package_service_id",
        PGUUID(as_uuid=True),
        ForeignKey("package_services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class PackageServiceLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single deliverable service line within a package.

    Examples in a "Premium Wedding Package":
    - 1x Photography 6 Hours (mandatory)
    - 1x DJ & Music (optional)
    - 1x Makeup Artist (optional)
    """

    __tablename__ = "package_services"

    __table_args__ = (
        Index("ix_package_services_package_id", "package_id"),
        Index("ix_package_services_category_id", "category_id"),
        Index("ix_package_services_display_order", "package_id", "display_order"),
        Index("ix_package_services_vendor_id", "vendor_id"),
        CheckConstraint(
            "(is_common AND package_id IS NULL) OR (NOT is_common AND package_id IS NOT NULL)",
            name="ck_package_services_common_xor_package",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    # NULL for common services (which live outside any single package and are
    # attached to N packages via package_service_links); required for
    # package-specific services, which keep the direct one-to-many shape.
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Set only for common services — the vendor who owns this reusable
    # service template. NULL for package-specific services (ownership is
    # inherited from the parent Package.vendor_id instead).
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_common: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for a vendor-owned reusable service template attached to "
                "packages via package_service_links; False for a normal "
                "package-specific service.",
    )

    # ── Service Classification ────────────────────────────────────────────────

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Links to VendorCategory for service type taxonomy (Photography, DJ, etc.)",
    )

    # ── Service Details ───────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Default/minimum quantity included in the package template (e.g. 2 photographers).",
    )

    max_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Highest quantity a customer may select for this service at booking "
                "time. NULL means uncapped — the customer can request any quantity >= `quantity`.",
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of quantity (e.g. 'hours', 'persons', 'sessions')",
    )

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Price of this service line within the package.",
    )

    # ── Flags ─────────────────────────────────────────────────────────────────

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Mandatory services are always included; optional services can be toggled off",
    )

    is_customizable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if the customer can configure options for this service",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Service's cover/thumbnail image, shown on service rows and as the "
                "first slide of its gallery (mirrors Package.cover_image_url)",
    )

    # ── Vendor Logistics ──────────────────────────────────────────────────────

    prep_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Vendor-suggested setup/prep time (minutes) required before the "
                "event's scheduled start. Copied onto BookingServiceItem at booking time.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package | None] = relationship(
        "Package",
        back_populates="services",
        lazy="noload",
    )

    category: Mapped[VendorCategory | None] = relationship(
        "VendorCategory",
        lazy="noload",
    )

    images: Mapped[list[PackageServiceImage]] = relationship(
        "PackageServiceImage",
        back_populates="service",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    # Packages this common service is attached to (empty for package-specific
    # services, which use package_id directly instead of this join table).
    linked_packages: Mapped[list[Package]] = relationship(
        "Package",
        secondary=package_service_links,
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageServiceLine id={self.id} name={self.name!r} "
            f"mandatory={self.is_mandatory}>"
        )
