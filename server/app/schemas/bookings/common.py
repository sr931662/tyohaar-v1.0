"""
Shared nested types and enum re-exports for the bookings domain.

Import from this module for booking-related sub-objects (e.g. financial
breakdowns) or enum values in other booking schema files.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    BookingStatus,
    BookingType,
    CancellationReason,
    Currency,
    InvoiceStatus,
    PaymentStatus,
)


__all__ = [
    # nested types
    "BookingFinancialsSchema",
    # enums
    "BookingStatus",
    "BookingType",
    "CancellationReason",
    "Currency",
    "InvoiceStatus",
    "PaymentStatus",
]


class BookingFinancialsSchema(BaseSchema):
    """
    Complete financial breakdown for a booking.

    All monetary amounts are non-negative Decimal values with 2 decimal
    places. This schema is used both as an embedded sub-object in
    BookingResponse and as the service-layer update payload when the
    pricing engine recalculates costs.
    """

    subtotal: MoneyAmount = Field(
        description="Sum of all package item prices before discounts and taxes"
    )
    discount_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Total discount applied (coupon + package-level discounts)",
    )
    tax_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="GST / applicable taxes computed on (subtotal - discount_amount)",
    )
    platform_fee: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Tyohaar platform service fee",
    )
    total_amount: MoneyAmount = Field(
        description="Final amount due = subtotal - discount_amount + tax_amount + platform_fee"
    )
    amount_paid: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Cumulative amount received from the customer so far",
    )
    amount_due: MoneyAmount = Field(
        description="Remaining balance = total_amount - amount_paid"
    )
