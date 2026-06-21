"""
Query-filter schemas for the bookings domain.

Used as FastAPI dependency-injected query-parameter models. All fields are
Optional; unset fields are ignored by the repository filter builder.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema
from app.models.enums import (
    BookingStatus,
    BookingType,
    PaymentStatus,
)


__all__ = [
    "BookingFilters",
    "BookingStatusHistoryFilters",
    "BookingCancellationFilters",
]


class BookingFilters(BaseSchema):
    """
    Filter set for querying Booking records.

    All conditions are ANDed. Date filters apply to scheduled_date.
    The search field does a case-insensitive prefix match on booking_number.
    """

    customer_id: uuid.UUID | None = Field(
        default=None, description="Filter bookings for a specific customer"
    )
    celebration_id: uuid.UUID | None = Field(
        default=None, description="Filter bookings within a specific celebration"
    )
    package_id: uuid.UUID | None = Field(
        default=None, description="Filter bookings for a specific package"
    )
    booking_type: BookingType | None = Field(
        default=None, description="Filter by booking type (PACKAGE, CUSTOM, etc.)"
    )
    booking_status: BookingStatus | None = Field(
        default=None, description="Filter by booking lifecycle status"
    )
    payment_status: PaymentStatus | None = Field(
        default=None, description="Filter by payment status"
    )
    from_date: date | None = Field(
        default=None, description="Return bookings with scheduled_date >= from_date"
    )
    to_date: date | None = Field(
        default=None, description="Return bookings with scheduled_date <= to_date"
    )
    search: str | None = Field(
        default=None,
        max_length=100,
        description="Case-insensitive search on booking_number",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "BookingFilters":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be ≤ to_date")
        return self


class BookingStatusHistoryFilters(BaseSchema):
    """Filter set for querying BookingStatusHistory audit records."""

    booking_id: uuid.UUID | None = Field(
        default=None, description="Retrieve history for a specific booking"
    )
    to_status: BookingStatus | None = Field(
        default=None, description="Filter entries that transitioned TO this status"
    )
    from_date: datetime | None = Field(
        default=None, description="Return entries where changed_at >= from_date (UTC)"
    )
    to_date: datetime | None = Field(
        default=None, description="Return entries where changed_at <= to_date (UTC)"
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "BookingStatusHistoryFilters":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be ≤ to_date")
        return self


class BookingCancellationFilters(BaseSchema):
    """Filter set for querying BookingCancellation records (admin use)."""

    booking_id: uuid.UUID | None = None
    cancelled_by_id: uuid.UUID | None = None
    from_date: datetime | None = Field(
        default=None, description="Filter cancellations on or after this UTC datetime"
    )
    to_date: datetime | None = Field(
        default=None, description="Filter cancellations on or before this UTC datetime"
    )
