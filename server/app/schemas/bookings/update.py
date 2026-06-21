"""
Update (PATCH body) schemas for the bookings domain.

All fields are Optional for partial updates. BookingFinancialsUpdate is
a service-layer-only schema — it must never be accepted directly from
client requests.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    BookingStatus,
    CancellationReason,
    PaymentStatus,
)


__all__ = [
    "BookingUpdate",
    "BookingFinancialsUpdate",
    "BookingInvoiceUpdate",
]


class BookingUpdate(BaseSchema):
    """
    Partial update payload for a Booking record.

    Clients may update scheduling fields, status transitions, and
    special instructions. Financial fields are managed exclusively by
    the service layer via BookingFinancialsUpdate.
    """

    scheduled_date: date | None = Field(
        default=None, description="New service date (triggers reschedule flow)"
    )
    scheduled_start_time: time | None = Field(
        default=None, description="New start time"
    )
    scheduled_end_time: time | None = Field(
        default=None, description="New end time"
    )
    booking_status: BookingStatus | None = Field(
        default=None, description="Target booking lifecycle state"
    )
    payment_status: PaymentStatus | None = Field(
        default=None,
        description="Denormalised payment status mirror — set by payment service only",
    )
    special_instructions: str | None = Field(
        default=None, description="Updated customer notes"
    )
    confirmed_at: datetime | None = Field(
        default=None, description="UTC datetime when the booking was confirmed"
    )
    completed_at: datetime | None = Field(
        default=None, description="UTC datetime when service delivery was completed"
    )
    cancellation_reason: CancellationReason | None = Field(
        default=None,
        description="Set when booking_status transitions to CANCELLED",
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingUpdate":
        if (
            self.scheduled_start_time is not None
            and self.scheduled_end_time is not None
            and self.scheduled_start_time >= self.scheduled_end_time
        ):
            raise ValueError("scheduled_start_time must be before scheduled_end_time")
        return self


class BookingFinancialsUpdate(BaseSchema):
    """
    Service-layer-only payload for updating booking financial fields.

    This schema is used internally by the pricing engine and payment
    service. It MUST NOT be exposed as a request body on any API endpoint.
    """

    subtotal: MoneyAmount
    discount_amount: MoneyAmount = Field(default=Decimal("0.00"))
    tax_amount: MoneyAmount = Field(default=Decimal("0.00"))
    platform_fee: MoneyAmount = Field(default=Decimal("0.00"))
    total_amount: MoneyAmount
    amount_paid: MoneyAmount = Field(default=Decimal("0.00"))
    amount_due: MoneyAmount

    @model_validator(mode="after")
    def validate_totals(self) -> "BookingFinancialsUpdate":
        expected_total = (
            self.subtotal
            - self.discount_amount
            + self.tax_amount
            + self.platform_fee
        )
        if abs(expected_total - self.total_amount) > Decimal("0.01"):
            raise ValueError(
                f"total_amount ({self.total_amount}) does not match "
                f"subtotal - discount + tax + fee ({expected_total})"
            )
        expected_due = self.total_amount - self.amount_paid
        if abs(expected_due - self.amount_due) > Decimal("0.01"):
            raise ValueError(
                f"amount_due ({self.amount_due}) does not match "
                f"total_amount - amount_paid ({expected_due})"
            )
        return self


class BookingInvoiceUpdate(BaseSchema):
    """Partial update payload for a BookingInvoice (admin/finance use)."""

    invoice_status: str | None = None
    issued_at: datetime | None = None
    due_at: datetime | None = None
    pdf_url: str | None = Field(default=None, max_length=2048)
