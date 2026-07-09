"""
Create (POST body) schemas for the bookings domain.

These are the shapes that clients or admin panels submit when initiating
a new booking, cancellation, or reschedule. Financial fields are
computed server-side and are not accepted on create.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema
from app.models.enums import (
    BookingType,
    CancellationReason,
    Currency,
)


__all__ = [
    "BookingCreate",
    "BookingCancellationCreate",
    "BookingRescheduleCreate",
]


class BookingCreate(BaseSchema):
    """
    Payload required to create a new booking.

    Financial fields (subtotal, taxes, totals) are intentionally absent —
    they are computed by the pricing service after creation and patched
    via BookingFinancialsUpdate.
    """

    celebration_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the celebration this booking belongs to. If omitted, the "
            "service auto-creates a minimal celebration from occasion_id/title/"
            "venue_address/scheduled_date so a customer can book a package "
            "without first walking through a separate celebration-planning step."
        ),
    )
    occasion_id: uuid.UUID | None = Field(
        default=None,
        description="Occasion type for celebration auto-creation. Falls back to the package's first linked occasion if omitted.",
    )
    celebration_title: str | None = Field(
        default=None,
        max_length=300,
        description="Title for the auto-created celebration (ignored if celebration_id is provided).",
    )
    venue_address: str | None = Field(
        default=None,
        description="Free-text venue address for the auto-created celebration (ignored if celebration_id is provided).",
    )
    package_id: uuid.UUID = Field(description="UUID of the package being booked")
    address_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the service-delivery address (optional for venue packages)",
    )
    recipient_name: str | None = None
    recipient_phone: str | None = None
    scheduled_date: date = Field(description="Date the service is scheduled to take place")
    scheduled_start_time: time | None = Field(
        default=None, description="Preferred start time (HH:MM:SS)"
    )
    scheduled_end_time: time | None = Field(
        default=None, description="Expected end time (HH:MM:SS)"
    )
    booking_type: BookingType = Field(
        default=BookingType.PACKAGE,
        description="Nature of the booking",
    )
    currency: Currency = Field(
        default=Currency.INR, description="Currency for all monetary fields"
    )
    special_instructions: str | None = Field(
        default=None,
        description="Free-form customer notes (allergies, decoration preferences, etc.)",
    )
    item_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="IDs of optional PackageItems (add-ons) selected by the user",
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingCreate":
        if (
            self.scheduled_start_time is not None
            and self.scheduled_end_time is not None
            and self.scheduled_start_time >= self.scheduled_end_time
        ):
            raise ValueError("scheduled_start_time must be before scheduled_end_time")
        return self


class BookingCancellationCreate(BaseSchema):
    """
    Payload required to cancel a booking.

    The service layer calculates cancellation_fee and refund_amount
    based on the cancellation policy; they are not accepted as input.
    """

    booking_id: uuid.UUID = Field(description="UUID of the booking to cancel")
    reason: CancellationReason = Field(description="Structured cancellation reason")
    reason_detail: str | None = Field(
        default=None,
        description="Optional free-text elaboration from the customer",
    )
    cancelled_by_id: uuid.UUID = Field(
        description="UUID of the user initiating the cancellation (customer or admin)"
    )


class BookingRescheduleCreate(BaseSchema):
    """
    Payload required to reschedule a booking to a new date/time.

    The previous date/time are copied from the current booking by the
    service layer and recorded in BookingReschedule for audit history.
    """

    booking_id: uuid.UUID = Field(description="UUID of the booking to reschedule")
    new_date: date = Field(description="New service date")
    new_start_time: time | None = Field(
        default=None, description="New preferred start time"
    )
    reason: str | None = Field(
        default=None,
        description="Optional reason for rescheduling",
    )
    rescheduled_by_id: uuid.UUID = Field(
        description="UUID of the user initiating the reschedule"
    )
