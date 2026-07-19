"""
Response schemas for the bookings domain.

All schemas use ConfigDict(from_attributes=True) for ORM compatibility.

SECURITY:
- internal_notes, extra_metadata, deleted_at are excluded from all
  public response schemas.
- BookingAssignment / vendor assignment details are never included
  in customer-facing responses (see internal.py for admin use).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    BookingStatus,
    BookingType,
    CancellationReason,
    Currency,
    InvoiceStatus,
    PaymentStatus,
    VerificationStatus,
)


__all__ = [
    "BookingResponse",
    "BookingItemResponse",
    "BookingCancellationResponse",
    "BookingRescheduleResponse",
    "BookingStatusHistoryResponse",
    "BookingInvoiceResponse",
    "BookingCustomerSummary",
    "BookingVendorSummary",
    "BookingDetailResponse",
]


class BookingCustomerSummary(BaseSchema):
    """
    Lightweight customer contact snapshot, attached to BookingDetailResponse
    for admin/support requesters only — never populated for customer or
    vendor callers of the same endpoint.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None


class BookingVendorSummary(BaseSchema):
    """
    Lightweight vendor summary for the package-owner vendor, attached to
    BookingDetailResponse for admin/support requesters only — never
    populated for customer or vendor callers of the same endpoint.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    business_name: str | None = None
    phone: str | None = None
    email: str | None = None
    verification_status: VerificationStatus | None = None


class BookingResponse(BaseSchema):
    """
    Public response shape for a Booking.

    Omitted fields: internal_notes, extra_metadata, deleted_at,
    vendor assignment details.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_number: str = Field(description="Human-readable booking reference, e.g. TYH-20240615-001234")
    customer_id: uuid.UUID
    celebration_id: uuid.UUID
    package_id: uuid.UUID
    package_name: str | None = Field(default=None, description="Snapshot of the package's current name")
    package_cover_url: str | None = Field(default=None, description="Snapshot of the package's current cover image")
    address_id: uuid.UUID | None
    scheduled_date: date
    scheduled_start_time: time | None
    scheduled_end_time: time | None
    booking_type: BookingType
    booking_status: BookingStatus
    payment_status: PaymentStatus
    currency: Currency
    # Financials
    subtotal: MoneyAmount
    discount_amount: MoneyAmount
    tax_amount: MoneyAmount
    platform_fee: MoneyAmount
    total_amount: MoneyAmount
    amount_paid: MoneyAmount
    amount_due: MoneyAmount
    preparation_start_time: time | None = Field(default=None, description="Legacy time-only mirror of preparation_start_at")
    preparation_start_at: datetime | None = Field(default=None, description="PST [Preparation Starting Time] — full date + time provided by the vendor")
    # Lifecycle timestamps
    confirmed_at: datetime | None
    completed_at: datetime | None
    # Customer-visible metadata
    special_instructions: str | None
    cancellation_reason: CancellationReason | None
    created_at: datetime
    updated_at: datetime


class BookingItemResponse(BaseSchema):
    """Public response shape for a BookingItem (price snapshot at booking time)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    package_item_id: uuid.UUID
    name: str = Field(description="Item name snapshotted at booking time")
    quantity: int
    unit_price: MoneyAmount
    final_price: MoneyAmount
    is_addon: bool = False
    notes: str | None
    scheduled_start_at: datetime | None = Field(
        default=None, description="When this specific service is scheduled to start"
    )
    prep_time_minutes: int | None = Field(
        default=None,
        description="Vendor-suggested setup/prep time (minutes) required before scheduled_start_at",
    )
    required_arrival_at: datetime | None = Field(
        default=None,
        description="Computed: scheduled_start_at minus prep_time_minutes — when the vendor must arrive",
    )
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _derive_required_arrival_at(self):
        if self.scheduled_start_at is not None and self.prep_time_minutes is not None:
            self.required_arrival_at = self.scheduled_start_at - timedelta(minutes=self.prep_time_minutes)
        return self


class BookingCancellationResponse(BaseSchema):
    """Public response shape for a BookingCancellation record."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    reason: CancellationReason
    reason_detail: str | None
    cancelled_by_id: uuid.UUID
    cancellation_fee: MoneyAmount | None
    refund_amount: MoneyAmount | None
    cancelled_at: datetime
    created_at: datetime
    updated_at: datetime


class BookingRescheduleResponse(BaseSchema):
    """Public response shape for a BookingReschedule audit record."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    previous_date: date
    new_date: date
    previous_start_time: time | None
    new_start_time: time | None
    reason: str | None
    rescheduled_by_id: uuid.UUID
    rescheduled_at: datetime
    created_at: datetime
    updated_at: datetime


class BookingStatusHistoryResponse(BaseSchema):
    """Public response shape for a BookingStatusHistory entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    from_status: BookingStatus | None
    to_status: BookingStatus
    changed_by_id: uuid.UUID | None
    reason: str | None
    changed_at: datetime
    created_at: datetime
    updated_at: datetime


class BookingInvoiceResponse(BaseSchema):
    """Public response shape for a BookingInvoice."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    invoice_number: str = Field(description="Unique invoice reference number")
    invoice_status: InvoiceStatus
    issued_at: datetime | None
    due_at: datetime | None
    subtotal: MoneyAmount
    tax_amount: MoneyAmount
    total_amount: MoneyAmount
    pdf_url: str | None
    created_at: datetime
    updated_at: datetime


class BookingDetailResponse(BookingResponse):
    """
    Extended booking response with all nested sub-resources.

    Returned by the booking detail endpoint. All related records are
    eager-loaded in a single repository query to avoid N+1 issues.
    Vendor assignment details are intentionally excluded — see
    BookingAssignmentInternal for admin-only access.
    """

    items: list[BookingItemResponse] = Field(
        default_factory=list, description="Line-item price snapshots"
    )
    cancellation: BookingCancellationResponse | None = Field(
        default=None, description="Cancellation record (if booking was cancelled)"
    )
    reschedules: list[BookingRescheduleResponse] = Field(
        default_factory=list, description="Ordered history of reschedule events"
    )
    invoices: list[BookingInvoiceResponse] = Field(
        default_factory=list, description="All invoices associated with this booking"
    )
    customer: BookingCustomerSummary | None = Field(
        default=None, description="Customer contact snapshot — admin/support requesters only"
    )
    vendor: BookingVendorSummary | None = Field(
        default=None, description="Package-owner vendor summary — admin/support requesters only"
    )
