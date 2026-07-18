"""
Query-filter schemas for the payments domain.

Used as FastAPI dependency-injected query-parameter models. All fields
are Optional; unset fields are ignored by the repository filter builder.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    CouponAdminStatus,
    CouponApplicability,
    CouponType,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
)
from app.schemas.payments.common import PaymentGatewayEnum


__all__ = [
    "PaymentFilters",
    "RefundFilters",
    "CouponFilters",
    "PaymentWebhookFilters",
]


class PaymentFilters(BaseSchema):
    """
    Filter set for querying Payment records.

    Date filters apply to created_at (UTC). Amount filters apply to
    final_amount. All conditions are ANDed.
    """

    booking_id: uuid.UUID | None = Field(
        default=None, description="Payments for a specific booking"
    )
    payer_id: uuid.UUID | None = Field(
        default=None, description="Payments made by a specific user"
    )
    payment_status: PaymentStatus | None = Field(
        default=None, description="Filter by payment lifecycle status"
    )
    payment_method: PaymentMethod | None = Field(
        default=None, description="Filter by payment instrument"
    )
    gateway: PaymentGatewayEnum | None = Field(
        default=None, description="Filter by processing gateway"
    )
    from_date: datetime | None = Field(
        default=None, description="Payments created on or after this UTC datetime"
    )
    to_date: datetime | None = Field(
        default=None, description="Payments created on or before this UTC datetime"
    )
    min_amount: MoneyAmount | None = Field(
        default=None, description="Minimum final_amount (inclusive)"
    )
    max_amount: MoneyAmount | None = Field(
        default=None, description="Maximum final_amount (inclusive)"
    )

    @model_validator(mode="after")
    def validate_ranges(self) -> "PaymentFilters":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be ≤ to_date")
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount must be ≤ max_amount")
        return self


class RefundFilters(BaseSchema):
    """Filter set for querying Refund records."""

    payment_id: uuid.UUID | None = Field(
        default=None, description="Refunds for a specific payment"
    )
    booking_id: uuid.UUID | None = Field(
        default=None, description="Refunds for a specific booking"
    )
    refund_status: RefundStatus | None = Field(
        default=None, description="Filter by refund lifecycle status"
    )
    from_date: datetime | None = Field(
        default=None, description="Refunds initiated on or after this UTC datetime"
    )
    to_date: datetime | None = Field(
        default=None, description="Refunds initiated on or before this UTC datetime"
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "RefundFilters":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be ≤ to_date")
        return self


class CouponFilters(BaseSchema):
    """
    Filter set for querying Coupon records.

    Date filters apply to valid_from (from_date) and valid_until (to_date).
    search does a case-insensitive match on both code and title.
    """

    coupon_type: CouponType | None = Field(
        default=None, description="Filter by discount mechanism"
    )
    applicability: CouponApplicability | None = Field(
        default=None, description="Filter by eligibility scope"
    )
    is_active: bool | None = Field(
        default=None, description="Return only active (or inactive) coupons"
    )
    is_system_generated: bool | None = Field(
        default=None, description="Return only platform-generated (or admin-created) coupons"
    )
    admin_status: CouponAdminStatus | None = Field(
        default=None, description="Filter by admin-controlled state (draft/published/paused/archived)"
    )
    is_automatic: bool | None = Field(
        default=None, description="Return only automatic (or only code-based) discounts"
    )
    search: str | None = Field(
        default=None,
        max_length=100,
        description="Case-insensitive search on code and title",
    )
    from_date: datetime | None = Field(
        default=None, description="Coupons with valid_from >= from_date"
    )
    to_date: datetime | None = Field(
        default=None, description="Coupons with valid_until <= to_date"
    )


class PaymentWebhookFilters(BaseSchema):
    """Filter set for querying PaymentWebhook records (admin use)."""

    gateway: str | None = Field(
        default=None, max_length=50, description="Filter by gateway name"
    )
    event_type: str | None = Field(
        default=None, max_length=100, description="Filter by event type"
    )
    is_processed: bool | None = Field(
        default=None, description="Return only processed (or pending) webhooks"
    )
    from_date: datetime | None = Field(
        default=None, description="Webhooks received on or after this UTC datetime"
    )
    to_date: datetime | None = Field(
        default=None, description="Webhooks received on or before this UTC datetime"
    )
