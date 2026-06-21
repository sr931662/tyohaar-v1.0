"""
Shared nested types and enum re-exports for the payments domain.

Defines the local PaymentGatewayEnum (stored as a string in the model,
not in the central enums registry because it is infrastructure-specific
and changes independently of domain logic).
"""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    CouponApplicability,
    CouponType,
    Currency,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
    TransactionType,
)


__all__ = [
    # local enum
    "PaymentGatewayEnum",
    # nested types
    "CouponValidationResult",
    # enums re-exported
    "CouponApplicability",
    "CouponType",
    "Currency",
    "PaymentMethod",
    "PaymentStatus",
    "RefundStatus",
    "TransactionType",
]


class PaymentGatewayEnum(str, enum.Enum):
    """
    Payment gateway identifiers stored as strings in the Payment model.

    Defined here (not in app.models.enums) because gateway choices are
    infrastructure-specific and may change without domain enum migrations.
    """

    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    CASHFREE = "cashfree"
    PHONEPE = "phonepe"
    PAYTM = "paytm"
    OFFLINE = "offline"


class CouponValidationResult(BaseSchema):
    """
    Result of a coupon eligibility check.

    Returned by the coupon validation service before a booking is
    confirmed. The client should display error_message when is_valid=False.
    """

    code: str = Field(description="The coupon code that was validated")
    is_valid: bool = Field(description="Whether the coupon can be applied to this booking")
    discount_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Computed discount if is_valid=True, else 0",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable reason why the coupon cannot be applied",
    )
