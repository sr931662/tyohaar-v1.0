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

from app.core.constants import BALLOON_COLOR_PALETTE
from app.schemas.base import BaseSchema
from app.models.enums import (
    BalloonColorMode,
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
    theme_id: uuid.UUID | None = Field(
        default=None,
        description="Customer's chosen visual theme for the auto-created celebration (ignored if celebration_id is provided).",
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
    customization_note: str | None = Field(
        default=None,
        max_length=2000,
        description="Customer's free-form custom requirements from the plan-flow "
                    "Details step, distinct from special_instructions. Visible to "
                    "both the vendor and Tyohaar admin.",
    )
    item_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="IDs of optional PackageItems (add-ons) selected by the user",
    )
    coupon_code: str | None = Field(
        default=None,
        max_length=50,
        description="Optional coupon code to apply — evaluated server-side by the discount engine alongside any automatic discounts",
    )
    item_quantities: dict[str, int] | None = Field(
        default=None,
        description="Optional per-item quantity override, keyed by PackageItem "
                    "id (as string). Applies to both mandatory and selected "
                    "optional items — e.g. a package ships 5 balloons by "
                    "default but the customer wants 15 for a bigger event. "
                    "Items not present here use the package template's default "
                    "quantity. Clamped server-side to [item.quantity, "
                    "item.max_quantity or unlimited].",
    )
    balloon_color_mode: BalloonColorMode | None = Field(
        default=None,
        description="Whether the customer wants a single accent balloon colour or a two-colour combination.",
    )
    balloon_colors: list[str] | None = Field(
        default=None,
        description="Hex code(s) of the chosen balloon colour(s) — must be drawn from "
                    "BALLOON_COLOR_PALETTE. Exactly 1 value for SINGLE mode, exactly 2 for DUAL.",
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

    @model_validator(mode="after")
    def validate_balloon_colors(self) -> "BookingCreate":
        if self.balloon_color_mode is None:
            if self.balloon_colors:
                raise ValueError("balloon_colors requires balloon_color_mode to be set")
            return self

        if not self.balloon_colors:
            raise ValueError("balloon_colors is required when balloon_color_mode is set")

        expected_count = 1 if self.balloon_color_mode == BalloonColorMode.SINGLE else 2
        if len(self.balloon_colors) != expected_count:
            raise ValueError(
                f"balloon_color_mode='{self.balloon_color_mode.value}' requires exactly "
                f"{expected_count} colour(s), got {len(self.balloon_colors)}"
            )

        allowed_hex = {hex_code.lower() for hex_code in BALLOON_COLOR_PALETTE.values()}
        normalized = [c.strip().lower() for c in self.balloon_colors]
        invalid = [c for c in normalized if c not in allowed_hex]
        if invalid:
            raise ValueError(
                f"Invalid balloon colour(s): {invalid}. Must be one of the curated "
                f"balloon palette: {list(BALLOON_COLOR_PALETTE.values())}"
            )
        if self.balloon_color_mode == BalloonColorMode.DUAL and normalized[0] == normalized[1]:
            raise ValueError("Dual balloon colour mode requires two different colours")

        self.balloon_colors = normalized
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
