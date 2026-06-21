"""
VendorService — a specific service offering by a vendor within a category.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PackagePricingType, ServiceStatus
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor
    from app.models.vendors.vendor_category import VendorCategory


class VendorService(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A discrete service or package offered by a vendor.

    One vendor can offer many services across different categories.
    E.g., a multi-service vendor might list:
    - "Birthday Balloon Decoration" (category: Decoration)
    - "Wedding Photography" (category: Photography)
    - "Drone Videography Add-on" (category: Videography)

    `price_details` JSONB is used for tiered pricing:
        [
            {"min_guests": 1,   "max_guests": 50,  "price": 15000.00},
            {"min_guests": 51,  "max_guests": 100, "price": 22000.00},
            {"min_guests": 101, "max_guests": 200, "price": 35000.00}
        ]

    For CUSTOM_QUOTE pricing, base_price is the starting/indicative price only.
    """

    __tablename__ = "vendor_services"

    __table_args__ = (
        Index("ix_vendor_services_vendor_id", "vendor_id"),
        Index("ix_vendor_services_category_id", "category_id"),
        Index("ix_vendor_services_status", "status", "is_active"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Service Details ───────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Internal name of this service (e.g., 'Premium Birthday Decoration Package')",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Pricing ───────────────────────────────────────────────────────────────

    pricing_type: Mapped[PackagePricingType] = mapped_column(
        SAEnum(PackagePricingType, name="package_pricing_type", native_enum=False),
        nullable=False,
        default=PackagePricingType.FIXED,
    )

    base_price: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Base/starting price in INR. For TIERED type, this is the minimum.",
    )

    price_details: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tier pricing steps. See module docstring for structure.",
    )

    # ── Capacity & Requirements ───────────────────────────────────────────────

    min_order_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum booking value to avail this service",
    )

    max_capacity_persons: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of guests/persons this service can cater to",
    )

    advance_booking_days: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Minimum number of days in advance this service must be booked",
    )

    experience_years: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Years of experience specifically in this service category",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    status: Mapped[ServiceStatus] = mapped_column(
        SAEnum(ServiceStatus, name="service_status", native_enum=False),
        nullable=False,
        default=ServiceStatus.ACTIVE,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="services")
    category: Mapped[VendorCategory] = relationship("VendorCategory", back_populates="services")

    def __repr__(self) -> str:
        return (
            f"<VendorService id={self.id} vendor_id={self.vendor_id} "
            f"name={self.name!r} status={self.status}>"
        )
