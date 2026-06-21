"""
BookingAssignment — internal mapping of a booking item to a vendor.

INTERNAL ONLY. This table is NEVER exposed in customer-facing API responses.
It drives Tyohaar's coordination engine for vendor dispatching.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AssignmentStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking_item import BookingItem
    from app.models.vendors.vendor import Vendor
    from app.models.users.user import User


class BookingAssignmentType(str, enum.Enum):
    """
    Whether this vendor is the primary or a backup for the booking item.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PRIMARY = "primary"
    BACKUP = "backup"


class BookingAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An assignment of a vendor to execute a specific service within a booking.

    Architecture:
    - One BookingItem can have one PRIMARY assignment and multiple BACKUP assignments.
    - BACKUP assignments are used when the primary vendor becomes unavailable.
    - `vendor_id` is INTERNAL. It must NEVER appear in customer-facing API responses.

    Workflow:
    1. Coordinator creates assignment (status=PENDING)
    2. Vendor accepts or rejects (status=ACCEPTED / REJECTED)
    3. On rejection, backup vendor is tried
    4. Once accepted, vendor is dispatched (status=DISPATCHED)
    5. On completion, status=COMPLETED

    `booking_id` is a denormalized FK (also derivable via booking_item.booking_id)
    included for fast admin dashboard queries over all assignments for a booking.

    `travel_distance_km` and `estimated_arrival_at` are used by the logistics
    coordinator to plan vendor dispatching and set customer expectations.
    """

    __tablename__ = "booking_assignments"

    __table_args__ = (
        UniqueConstraint(
            "booking_item_id",
            "vendor_id",
            name="uq_booking_assignments_item_vendor",
        ),
        Index("ix_booking_assignments_booking_id", "booking_id"),
        Index("ix_booking_assignments_booking_item_id", "booking_item_id"),
        Index("ix_booking_assignments_vendor_id", "vendor_id"),
        Index("ix_booking_assignments_status", "assignment_status"),
    )

    # ── Context (denormalized for fast queries) ───────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        comment="Denormalized from booking_item.booking_id for admin dashboard queries",
    )

    booking_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("booking_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Vendor (INTERNAL) ─────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        comment="INTERNAL. The assigned vendor. NEVER expose to customers.",
    )

    # ── Assignment Details ────────────────────────────────────────────────────

    assignment_type: Mapped[BookingAssignmentType] = mapped_column(
        SAEnum(BookingAssignmentType, name="booking_assignment_type", native_enum=False),
        nullable=False,
        default=BookingAssignmentType.PRIMARY,
    )

    priority_rank: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        comment="1 = primary, 2 = first backup, 3 = second backup, etc.",
    )

    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, name="assignment_status", native_enum=False),
        nullable=False,
    )

    # ── Who Assigned ─────────────────────────────────────────────────────────

    assigned_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tyohaar coordinator who made this assignment. NULL if system-assigned.",
    )

    # ── Vendor Response ───────────────────────────────────────────────────────

    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Logistics ─────────────────────────────────────────────────────────────

    travel_distance_km: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Distance from vendor base to celebration venue in km",
    )

    estimated_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="ETA at the celebration venue",
    )

    actual_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────

    assignment_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal coordination notes (never expose to customer or vendor)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking_item: Mapped[BookingItem] = relationship(
        "BookingItem",
        back_populates="assignments",
        lazy="noload",
    )

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="noload")

    assigned_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingAssignment id={self.id} item={self.booking_item_id} "
            f"vendor={self.vendor_id} status={self.assignment_status}>"
        )
