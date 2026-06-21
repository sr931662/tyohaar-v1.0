"""
Internal-only schemas for the bookings domain.

These schemas are NEVER serialised to public API responses. They are used
exclusively within the service/repository layers, background jobs, and
admin-only endpoints.

WARNING:
- BookingInternal exposes internal_notes, extra_metadata, and deleted_at.
- BookingAssignmentInternal exposes vendor assignment details.
  NEITHER must ever appear in customer-facing response schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import AssignmentStatus
from app.schemas.bookings.response import BookingResponse


__all__ = [
    "BookingInternal",
    "BookingAssignmentInternal",
]


class BookingInternal(BookingResponse):
    """
    Full booking record including admin-only and soft-delete fields.

    Extends the public BookingResponse with fields that must remain
    server-side only. Use only in admin service handlers and background
    jobs — never pass to customer-facing serialisers.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    internal_notes: str | None = Field(
        default=None,
        description="Admin-only free-text notes on this booking",
    )
    extra_metadata: dict | None = Field(
        default=None,
        description="Arbitrary key-value metadata for integrations (internal)",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp; None means record is live",
    )


class BookingAssignmentInternal(BaseSchema):
    """
    Vendor assignment details for a booking — ADMIN AND INTERNAL USE ONLY.

    This schema exposes which vendor has been assigned to fulfil a booking.
    It must NEVER be included in customer-facing responses to avoid
    revealing internal vendor routing, pricing, or capacity information.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    vendor_id: uuid.UUID = Field(description="UUID of the assigned vendor")
    assigned_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin who made the assignment (None = auto-assigned)",
    )
    assignment_status: AssignmentStatus = Field(
        description="Current status of the vendor assignment"
    )
    vendor_fee: MoneyAmount | None = Field(
        default=None,
        description="Agreed payout to the vendor for this booking",
    )
    platform_margin: MoneyAmount | None = Field(
        default=None,
        description="Platform margin retained (total - vendor_fee)",
    )
    assigned_at: datetime
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = Field(
        default=None,
        description="Internal notes on the assignment (visible to ops team only)",
    )
    created_at: datetime
    updated_at: datetime
