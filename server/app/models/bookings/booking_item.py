"""
BookingItem — a single service line within a booking.

Examples: Balloon Decoration, Birthday Cake 1kg, Photography 2hr, DJ Setup.
Vendor assigned to deliver each item is tracked in BookingAssignment (internal).
"""

from __future__ import annotations

import enum
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.bookings.booking_assignment import BookingAssignment
    from app.models.packages.package_item import PackageItem
    from app.models.packages.package_addon import PackageAddon
    from app.models.vendors.vendor_category import VendorCategory


class BookingItemStatus(str, enum.Enum):
    """
    Delivery/execution status of a single service item within a booking.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class BookingItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single deliverable service line within a booking.

    Each BookingItem represents one service (Decoration, Photography, Cake, etc.)
    that must be executed as part of the overall booking.

    `package_item_id` links back to the PackageItem template this was cloned from.
    `addon_id` links back to the PackageAddon if this item is an optional addon.
    `vendor_category_id` classifies the service type for admin operations.

    Vendor assignment for this item is tracked in `BookingAssignment` (internal).
    Customers see item names and statuses, but NEVER vendor details.

    Financial fields (all Numeric(12, 2)):
    - `unit_price`:      Per-unit price charged to the customer
    - `quantity`:        Number of units
    - `discount_amount`: Item-level discount applied
    - `final_price`:     = (unit_price × quantity) − discount_amount
    """

    __tablename__ = "booking_items"

    __table_args__ = (
        Index("ix_booking_items_booking_id", "booking_id"),
        Index("ix_booking_items_package_item_id", "package_item_id"),
        Index("ix_booking_items_status", "booking_id", "service_status"),
        CheckConstraint("quantity >= 1", name="ck_booking_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_booking_item_unit_price_non_negative"),
        CheckConstraint("discount_amount >= 0", name="ck_booking_item_discount_non_negative"),
        CheckConstraint("final_price >= 0", name="ck_booking_item_final_price_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Source Template ───────────────────────────────────────────────────────

    package_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="SET NULL"),
        nullable=True,
        comment="Source PackageItem this was created from. NULL for custom/addon items.",
    )

    addon_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_addons.id", ondelete="SET NULL"),
        nullable=True,
        comment="Source PackageAddon if this item is an optional upgrade.",
    )

    vendor_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Service type classification (Decoration, Photography, etc.)",
    )

    # ── Item Details ──────────────────────────────────────────────────────────

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
        comment="Unit of measure (e.g. 'hours', 'kg', 'pieces')",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Per-unit price charged to the customer",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    final_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="(unit_price × quantity) − discount_amount. Computed and stored by service layer.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    service_status: Mapped[BookingItemStatus] = mapped_column(
        SAEnum(BookingItemStatus, name="booking_item_status", native_enum=False),
        nullable=False,
        default=BookingItemStatus.PENDING,
    )

    is_addon: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if this item was added as an optional upgrade",
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Copied from PackageItem.is_mandatory at booking time",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this specific service is scheduled to start",
    )

    actual_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the vendor actually started this service",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal coordination notes for this service item",
    )

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Vendor Logistics ──────────────────────────────────────────────────────

    prep_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Vendor-suggested setup/prep time (minutes) required before "
                "scheduled_start_at. Snapshotted from PackageItem.prep_time_minutes "
                "at booking time; vendor may override after assignment.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="items",
        lazy="noload",
    )

    package_item: Mapped[PackageItem | None] = relationship(
        "PackageItem",
        lazy="noload",
    )

    addon: Mapped[PackageAddon | None] = relationship(
        "PackageAddon",
        lazy="noload",
    )

    vendor_category: Mapped[VendorCategory | None] = relationship(
        "VendorCategory",
        lazy="noload",
    )

    assignments: Mapped[list[BookingAssignment]] = relationship(
        "BookingAssignment",
        back_populates="booking_item",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingItem id={self.id} name={self.name!r} "
            f"status={self.service_status} price={self.final_price}>"
        )
