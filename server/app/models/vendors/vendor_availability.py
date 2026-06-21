"""
Vendor availability management — recurring weekly schedule and blocked periods.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import DayOfWeek
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorBlockType(str, enum.Enum):
    """
    Reason category for a blocked period in the vendor's calendar.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    VACATION = "vacation"
    EMERGENCY_CLOSURE = "emergency_closure"
    PUBLIC_HOLIDAY = "public_holiday"
    MAINTENANCE = "maintenance"
    PERSONAL = "personal"
    FULLY_BOOKED = "fully_booked"   # Vendor manually marks themselves full
    OTHER = "other"


class VendorWorkSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Recurring weekly availability for a vendor.

    One row per (vendor_id, day_of_week) pair — 7 rows max per vendor,
    enforced by the unique constraint. `is_working = False` on a row means
    the vendor does not work on that day.

    `max_bookings_per_day` caps concurrent booking assignments per day,
    preventing overbooking in the assignment engine.

    `break_start` / `break_end` model a single midday break. Extend to a
    JSONB array if multiple breaks per day are needed in the future.
    """

    __tablename__ = "vendor_work_schedules"

    __table_args__ = (
        UniqueConstraint("vendor_id", "day_of_week", name="uq_vendor_work_schedule_day"),
        Index("ix_vendor_work_schedules_vendor_id", "vendor_id"),
        CheckConstraint("max_bookings_per_day > 0", name="ck_max_bookings_positive"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Schedule ──────────────────────────────────────────────────────────────

    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SAEnum(DayOfWeek, name="day_of_week", native_enum=False),
        nullable=False,
    )

    is_working: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False if the vendor does not work on this day of the week",
    )

    open_time: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
        comment="Local time when the vendor starts work (null if not working)",
    )

    close_time: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
        comment="Local time when the vendor ends work (null if not working)",
    )

    break_start: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
        comment="Start of midday break (null if no break)",
    )

    break_end: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
        comment="End of midday break (null if no break)",
    )

    max_bookings_per_day: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        comment="Maximum bookings the vendor can accept on this day of the week",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="work_schedule")

    def __repr__(self) -> str:
        return (
            f"<VendorWorkSchedule vendor_id={self.vendor_id} "
            f"day={self.day_of_week} working={self.is_working}>"
        )


class VendorBlockedPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A specific date range during which the vendor is unavailable.

    Blocked periods override the recurring work schedule. The assignment
    engine must check both this table and VendorWorkSchedule before
    assigning a vendor to a booking.

    Date ranges are inclusive on both ends.
    """

    __tablename__ = "vendor_blocked_periods"

    __table_args__ = (
        Index("ix_vendor_blocked_periods_vendor_id", "vendor_id"),
        Index("ix_vendor_blocked_periods_dates", "vendor_id", "start_date", "end_date"),
        CheckConstraint("end_date >= start_date", name="ck_blocked_period_dates_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Period ────────────────────────────────────────────────────────────────

    block_type: Mapped[VendorBlockType] = mapped_column(
        SAEnum(VendorBlockType, name="vendor_block_type", native_enum=False),
        nullable=False,
        default=VendorBlockType.OTHER,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Inclusive end date. Same as start_date for a single-day block.",
    )

    # ── Context ───────────────────────────────────────────────────────────────

    reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Brief reason visible to Tyohaar staff (not to customers)",
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_all_day: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False if the block applies only to specific hours (extend model if needed)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="blocked_periods")

    def __repr__(self) -> str:
        return (
            f"<VendorBlockedPeriod vendor_id={self.vendor_id} "
            f"type={self.block_type} {self.start_date}→{self.end_date}>"
        )
