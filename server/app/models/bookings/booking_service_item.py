"""
BookingServiceItem — a single service line within a booking.

Mirrors BookingItem exactly (see booking_item.py) but snapshots a
PackageServiceLine (labor/service, e.g. Photography, DJ) rather than a
PackageItem (physical item) at booking time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.bookings.booking_item import BookingItemStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.packages.package_service import PackageServiceLine
    from app.models.vendors.vendor_category import VendorCategory


class BookingServiceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single deliverable service line within a booking.

    `package_service_id` links back to the PackageServiceLine template this
    was cloned from.

    Financial fields (all Numeric(12, 2)):
    - `unit_price`:      Per-unit price charged to the customer
    - `quantity`:        Number of units
    - `final_price`:     = unit_price × quantity
    """

    __tablename__ = "booking_service_items"

    __table_args__ = (
        Index("ix_booking_service_items_booking_id", "booking_id"),
        Index("ix_booking_service_items_package_service_id", "package_service_id"),
        CheckConstraint("quantity >= 1", name="ck_booking_service_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_booking_service_item_unit_price_non_negative"),
        CheckConstraint("final_price >= 0", name="ck_booking_service_item_final_price_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Source Template ───────────────────────────────────────────────────────

    package_service_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_services.id", ondelete="SET NULL"),
        nullable=True,
        comment="Source PackageServiceLine this was created from.",
    )

    vendor_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Service type classification (Photography, DJ, etc.)",
    )

    # ── Service Details ───────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Service name copied from package at booking time (immutable snapshot)",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Pricing ───────────────────────────────────────────────────────────────

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of measure (e.g. 'hours', 'persons')",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Per-unit price charged to the customer",
    )

    final_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="unit_price × quantity. Computed and stored by service layer.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    service_status: Mapped[BookingItemStatus] = mapped_column(
        SAEnum(BookingItemStatus, name="booking_service_item_status", native_enum=False),
        nullable=False,
        default=BookingItemStatus.PENDING,
    )

    is_addon: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if this service was added as an optional selection",
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Copied from PackageServiceLine.is_mandatory at booking time",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this specific service is scheduled to start",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Vendor Logistics ──────────────────────────────────────────────────────

    prep_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Vendor-suggested setup/prep time (minutes) required before "
                "scheduled_start_at. Snapshotted from PackageServiceLine.prep_time_minutes "
                "at booking time.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="service_items",
        lazy="noload",
    )

    package_service: Mapped[PackageServiceLine | None] = relationship(
        "PackageServiceLine",
        lazy="noload",
    )

    vendor_category: Mapped[VendorCategory | None] = relationship(
        "VendorCategory",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingServiceItem id={self.id} name={self.name!r} "
            f"status={self.service_status} price={self.final_price}>"
        )
