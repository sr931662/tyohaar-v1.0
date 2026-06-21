"""
Create (POST body) schemas for the payments domain.

Defines the request shapes for initiating payments, refunds, coupon
creation, and coupon validation. gateway_signature is never accepted
as input — it is computed server-side during webhook verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    CouponApplicability,
    CouponType,
    Currency,
    PaymentMethod,
)
from app.schemas.payments.common import PaymentGatewayEnum


__all__ = [
    "PaymentCreate",
    "RefundCreate",
    "CouponCreate",
    "CouponValidateRequest",
]


class PaymentCreate(BaseSchema):
    """
    Payload required to initiate a new payment.

    The service layer creates a gateway order from these fields and
    returns a gateway_order_id to the client for checkout.
    gateway_signature is never accepted as input.
    """

    booking_id: uuid.UUID = Field(description="UUID of the booking being paid for")
    payer_id: uuid.UUID = Field(description="UUID of the user making the payment")
    currency: Currency = Field(default=Currency.INR, description="Payment currency")
    subtotal: MoneyAmount = Field(description="Order subtotal before discounts and fees")
    discount_amount: MoneyAmount = Field(
        default=Decimal("0.00"), description="Total discount applied"
    )
    tax_amount: MoneyAmount = Field(
        default=Decimal("0.00"), description="GST / applicable taxes"
    )
    platform_fee: MoneyAmount = Field(
        default=Decimal("0.00"), description="Tyohaar platform service fee"
    )
    final_amount: MoneyAmount = Field(
        description="Amount to charge = subtotal - discount + tax + platform_fee"
    )
    payment_method: PaymentMethod | None = Field(
        default=None,
        description="Preferred payment instrument (may be selected later in checkout)",
    )
    gateway: PaymentGatewayEnum | None = Field(
        default=None,
        description="Target payment gateway (defaults to platform setting if None)",
    )

    @model_validator(mode="after")
    def validate_final_amount(self) -> "PaymentCreate":
        expected = (
            self.subtotal
            - self.discount_amount
            + self.tax_amount
            + self.platform_fee
        )
        if abs(expected - self.final_amount) > Decimal("0.01"):
            raise ValueError(
                f"final_amount ({self.final_amount}) does not match "
                f"subtotal - discount + tax + fee ({expected})"
            )
        return self


class RefundCreate(BaseSchema):
    """
    Payload required to initiate a refund.

    Refund amount must not exceed the original payment's final_amount.
    The service layer validates this constraint against the database.
    """

    payment_id: uuid.UUID = Field(description="UUID of the payment to refund")
    booking_id: uuid.UUID = Field(description="UUID of the associated booking")
    amount: MoneyAmount = Field(description="Amount to refund (must be > 0)")
    currency: Currency = Field(default=Currency.INR)
    reason: str | None = Field(
        default=None,
        description="Free-text reason for the refund (stored for audit trail)",
    )
    initiated_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin or system UUID initiating the refund (None = automated)",
    )

    @field_validator("amount", mode="after")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Refund amount must be greater than 0")
        return v


class CouponCreate(BaseSchema):
    """
    Admin payload required to create a new coupon.

    code is normalised to uppercase on input. internal_notes is accepted
    here (admin-only create endpoint) but excluded from public responses.
    """

    code: str = Field(
        min_length=3,
        max_length=50,
        description="Coupon code (auto-uppercased and stripped)",
    )
    title: str = Field(min_length=1, max_length=200, description="Short display title")
    description: str | None = Field(default=None, description="Detailed description")
    coupon_type: CouponType = Field(description="Discount mechanism type")
    applicability: CouponApplicability = Field(description="Which bookings are eligible")
    discount_value: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Percentage (0-100) or fixed amount depending on coupon_type",
    )
    max_discount_amount: MoneyAmount | None = Field(
        default=None,
        description="Cap applied to PERCENTAGE discounts (e.g. max ₹500 off)",
    )
    currency: Currency = Field(default=Currency.INR)
    min_order_value: MoneyAmount | None = Field(
        default=None,
        description="Minimum booking subtotal required to apply this coupon",
    )
    first_booking_only: bool = Field(
        default=False,
        description="Restrict to users who have never booked before",
    )
    eligible_membership_tiers: list[str] | None = Field(
        default=None,
        description="Membership tier names eligible for this coupon (MEMBERSHIP_ONLY type)",
    )
    applicable_vendor_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific vendor UUIDs this coupon applies to (SPECIFIC_VENDOR type)",
    )
    applicable_package_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific package UUIDs this coupon applies to (SPECIFIC_PACKAGE type)",
    )
    applicable_occasion_categories: list[str] | None = Field(
        default=None,
        description="Occasion category values this coupon targets (SPECIFIC_CATEGORY type)",
    )
    total_usage_limit: int | None = Field(
        default=None, ge=1, description="Maximum total redemptions across all users"
    )
    per_user_limit: int | None = Field(
        default=None, ge=1, description="Maximum redemptions per individual user"
    )
    valid_from: datetime = Field(description="UTC datetime when coupon becomes active")
    valid_until: datetime | None = Field(
        default=None, description="UTC datetime when coupon expires (None = never)"
    )
    is_system_generated: bool = Field(
        default=False,
        description="True for platform-generated coupons (referral rewards, etc.)",
    )
    internal_notes: str | None = Field(
        default=None,
        description="Admin-only notes — never exposed in public responses",
    )

    @field_validator("code", mode="before")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_coupon_consistency(self) -> "CouponCreate":
        if (
            self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be before valid_until")
        if (
            self.coupon_type == CouponType.PERCENTAGE
            and self.discount_value > Decimal("100")
        ):
            raise ValueError("discount_value cannot exceed 100 for PERCENTAGE coupons")
        return self


class CouponValidateRequest(BaseSchema):
    """
    Request body for the coupon validation endpoint.

    Used before checkout to check if a code can be applied to the
    customer's current basket. The service returns a CouponValidationResponse.
    """

    code: str = Field(min_length=1, max_length=50, description="Coupon code to validate")
    booking_subtotal: MoneyAmount = Field(
        description="Current basket subtotal to check min_order_value against"
    )
    user_id: uuid.UUID = Field(description="UUID of the customer applying the coupon")

    @field_validator("code", mode="before")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.upper().strip()
