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
    CouponAdminStatus,
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
    "DiscountPreviewRequest",
]


class PaymentCreate(BaseSchema):
    """
    Payload required to initiate a new payment.

    booking_id is taken from the URL path and payer_id from the authenticated
    user — neither is accepted here, to avoid a client being able to spoof
    who is paying for what. The service layer creates a gateway order from
    these fields and returns a gateway_order_id to the client for checkout.
    gateway_signature is never accepted as input.
    """

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

    code: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="Coupon code (auto-uppercased and stripped). Omit for an automatic discount.",
    )
    is_automatic: bool = Field(
        default=False,
        description="True = no code required; the engine evaluates eligibility automatically.",
    )
    title: str = Field(min_length=1, max_length=200, description="Internal/admin display name")
    public_offer_title: str | None = Field(
        default=None,
        max_length=300,
        description="Customer-facing marketing title, e.g. 'Diwali Dhamaka — 15% OFF!'",
    )
    description: str | None = Field(default=None, description="Internal description")
    terms_and_conditions: str | None = Field(
        default=None, description="Customer-facing terms & conditions"
    )
    coupon_type: CouponType = Field(description="Discount mechanism type")
    applicability: CouponApplicability = Field(description="Which bookings are eligible")
    discount_value: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Percentage (0-100), fixed amount, or target fixed price depending on coupon_type",
    )
    max_discount_amount: MoneyAmount | None = Field(
        default=None,
        description="Cap applied to PERCENTAGE discounts (e.g. max ₹500 off)",
    )
    currency: Currency = Field(default=Currency.INR)
    priority: int = Field(
        default=100,
        description="Lower number = preferred first when multiple non-stackable discounts are eligible",
    )
    is_stackable: bool = Field(
        default=False,
        description="True = can combine with other eligible discounts",
    )
    condition_rules: dict | None = Field(
        default=None,
        description=(
            "Condition tree for date/behavior-based automatic discounts "
            "(Weekend Offer, Happy Hours, Birthday Month) — "
            "{'op': 'AND'|'OR', 'clauses': [{'field','operator','value'}]}"
        ),
    )
    admin_status: CouponAdminStatus = Field(
        default=CouponAdminStatus.DRAFT,
        description="Admin-controlled state (draft/published/paused/archived)",
    )
    banner_image_url: str | None = Field(default=None, max_length=2048)
    theme_color_hex: str | None = Field(default=None)
    min_order_value: MoneyAmount | None = Field(
        default=None,
        description="Minimum booking subtotal required to apply this coupon",
    )
    min_package_value: MoneyAmount | None = Field(
        default=None,
        description="Minimum price of the specific package being booked (distinct from min_order_value)",
    )
    first_booking_only: bool = Field(
        default=False,
        description="Restrict to users who have never booked before",
    )
    repeat_customers_only: bool = Field(
        default=False,
        description="Restrict to users with at least one prior completed booking",
    )
    referral_users_only: bool = Field(
        default=False,
        description="Restrict to users who signed up via a referral",
    )
    eligible_membership_tiers: list[str] | None = Field(
        default=None,
        description="Membership tier names eligible for this coupon (MEMBERSHIP_ONLY type)",
    )
    eligible_customer_group_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Reserved for future use — no customer-group entity exists yet",
    )
    applicable_vendor_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific vendor UUIDs this coupon applies to (SPECIFIC_VENDOR type)",
    )
    applicable_package_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific package UUIDs this coupon applies to (SPECIFIC_PACKAGE type)",
    )
    applicable_occasion_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific occasion UUIDs this coupon applies to",
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
    max_uses_per_day: int | None = Field(
        default=None, ge=1, description="Maximum redemptions platform-wide per calendar day (UTC)"
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
    def normalise_code(cls, v: str | None) -> str | None:
        return v.upper().strip() if v else v

    @field_validator("theme_color_hex")
    @classmethod
    def validate_theme_color_hex(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise ValueError("theme_color_hex must be a 6-digit hex color, e.g. '#C8A96E'")
        return v

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
        if self.coupon_type in (CouponType.BUY_X_GET_Y, CouponType.FREE_ADDON):
            raise ValueError(
                f"coupon_type '{self.coupon_type.value}' is reserved for future use "
                "and cannot be created yet."
            )
        if self.is_automatic and self.code is not None:
            raise ValueError("An automatic discount cannot also have a coupon code.")
        if not self.is_automatic and self.code is None:
            raise ValueError("code is required unless is_automatic is True.")
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


class DiscountPreviewRequest(BaseSchema):
    """
    Request body for the full discount-engine preview endpoint.

    Returns every applicable discount (automatic + the given coupon code,
    if any) combined per the engine's priority/stacking rules — the same
    evaluation `create_booking` uses to compute `discount_amount`, exposed
    read-only for checkout-time price display.
    """

    subtotal: MoneyAmount = Field(description="Current basket subtotal before any discount")
    package_id: uuid.UUID | None = Field(default=None)
    occasion_id: uuid.UUID | None = Field(default=None)
    coupon_code: str | None = Field(
        default=None, max_length=50, description="Optional coupon code to also evaluate"
    )

    @field_validator("coupon_code", mode="before")
    @classmethod
    def normalise_coupon_code(cls, v: str | None) -> str | None:
        return v.upper().strip() if v else v
