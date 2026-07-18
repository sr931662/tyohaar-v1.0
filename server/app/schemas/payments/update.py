"""
Update (PATCH body) schemas for the payments domain.

All fields are Optional for partial updates. gateway_signature is
intentionally absent — it is never accepted or returned via API.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

import uuid

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    CouponAdminStatus,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
)
from app.schemas.payments.common import PaymentGatewayEnum


__all__ = [
    "PaymentUpdate",
    "RefundUpdate",
    "CouponUpdate",
]


class PaymentUpdate(BaseSchema):
    """
    Partial update for a Payment record.

    Used by the payment service to record gateway callbacks (captured,
    settled, failed) and by admin endpoints to correct status. Fields
    such as booking_id, payer_id, and amounts are immutable after creation.
    gateway_signature is never accepted as input.
    """

    payment_status: PaymentStatus | None = Field(
        default=None, description="New lifecycle status"
    )
    payment_method: PaymentMethod | None = Field(
        default=None,
        description="Payment instrument confirmed by gateway (may differ from intent)",
    )
    gateway: PaymentGatewayEnum | None = Field(
        default=None, description="Gateway that processed the payment"
    )
    gateway_order_id: str | None = Field(
        default=None,
        max_length=200,
        description="Gateway-assigned order/session identifier",
    )
    gateway_payment_id: str | None = Field(
        default=None,
        max_length=200,
        description="Gateway-assigned payment/transaction identifier",
    )
    captured_at: datetime | None = Field(
        default=None, description="UTC datetime when payment was captured"
    )
    settled_at: datetime | None = Field(
        default=None, description="UTC datetime when funds were settled"
    )
    failed_at: datetime | None = Field(
        default=None, description="UTC datetime when payment failed"
    )


class RefundUpdate(BaseSchema):
    """Partial update for a Refund record (used by gateway webhook handlers)."""

    refund_status: RefundStatus | None = Field(
        default=None, description="New refund lifecycle status"
    )
    gateway_refund_id: str | None = Field(
        default=None,
        max_length=200,
        description="Gateway-assigned refund identifier",
    )
    initiated_at: datetime | None = Field(
        default=None, description="UTC datetime when refund was initiated at gateway"
    )
    completed_at: datetime | None = Field(
        default=None, description="UTC datetime when refund reached the customer"
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "RefundUpdate":
        if (
            self.initiated_at is not None
            and self.completed_at is not None
            and self.initiated_at > self.completed_at
        ):
            raise ValueError("initiated_at must be before or equal to completed_at")
        return self


class CouponUpdate(BaseSchema):
    """
    Partial update for a Coupon record (admin use).

    code, coupon_type, applicability, and financial amounts (other than
    discount_value) are immutable after creation to preserve audit integrity.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    public_offer_title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    terms_and_conditions: str | None = None
    discount_value: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Updated discount magnitude",
    )
    max_discount_amount: MoneyAmount | None = None
    priority: int | None = Field(default=None)
    is_stackable: bool | None = Field(default=None)
    condition_rules: dict | None = None
    admin_status: CouponAdminStatus | None = Field(
        default=None, description="Admin-controlled state (draft/published/paused/archived)"
    )
    banner_image_url: str | None = Field(default=None, max_length=2048)
    theme_color_hex: str | None = Field(default=None)
    min_order_value: MoneyAmount | None = None
    min_package_value: MoneyAmount | None = None
    first_booking_only: bool | None = Field(default=None)
    repeat_customers_only: bool | None = Field(default=None)
    referral_users_only: bool | None = Field(default=None)
    eligible_membership_tiers: list[str] | None = None
    eligible_customer_group_ids: list[uuid.UUID] | None = None
    applicable_vendor_ids: list[uuid.UUID] | None = None
    applicable_package_ids: list[uuid.UUID] | None = None
    applicable_occasion_ids: list[uuid.UUID] | None = None
    applicable_occasion_categories: list[str] | None = None
    total_usage_limit: int | None = Field(default=None, ge=1)
    per_user_limit: int | None = Field(default=None, ge=1)
    max_uses_per_day: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = Field(
        default=None, description="Enable or disable the coupon"
    )
    deactivated_at: datetime | None = Field(
        default=None,
        description="UTC datetime when the coupon was deactivated (set by service layer)",
    )

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
    def validate_date_range(self) -> "CouponUpdate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be before valid_until")
        return self
