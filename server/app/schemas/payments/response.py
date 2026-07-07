"""
Response schemas for the payments domain.

All schemas use ConfigDict(from_attributes=True) for ORM compatibility.

SECURITY GUARANTEES (enforced by field exclusion — not runtime filtering):
- gateway_signature: NEVER included in any response schema (HMAC secret)
- PaymentWebhookResponse.payload: excluded (can be megabytes of raw JSON)
- PaymentWebhookResponse.signature: excluded (security-sensitive)
- CouponResponse: excludes internal_notes, eligible_membership_tiers,
  applicable_vendor_ids, applicable_package_ids (internal targeting data)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, computed_field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    CouponApplicability,
    CouponType,
    Currency,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
)
from app.schemas.payments.common import PaymentGatewayEnum


__all__ = [
    "PaymentResponse",
    "RefundResponse",
    "CouponResponse",
    "CouponPublicResponse",
    "CouponValidationResponse",
    "PaymentWebhookResponse",
]


class PaymentResponse(BaseSchema):
    """
    Public response shape for a Payment.

    gateway_signature is intentionally excluded — it is an HMAC-SHA256
    secret used for webhook verification and must never leave the server.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    payment_number: str = Field(description="Human-readable reference, e.g. PAY-2024-001234")
    booking_id: uuid.UUID
    payer_id: uuid.UUID
    currency: Currency
    subtotal: MoneyAmount
    discount_amount: MoneyAmount
    tax_amount: MoneyAmount
    platform_fee: MoneyAmount
    final_amount: MoneyAmount
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    gateway: PaymentGatewayEnum | None
    gateway_order_id: str | None = Field(
        default=None,
        description="Gateway order ID — needed by client SDKs to open checkout",
    )
    gateway_payment_id: str | None = Field(
        default=None,
        description="Gateway payment ID — set after successful capture",
    )
    # gateway_signature intentionally omitted
    captured_at: datetime | None
    settled_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RefundResponse(BaseSchema):
    """Public response shape for a Refund."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    amount: MoneyAmount
    currency: Currency
    refund_status: RefundStatus
    reason: str | None = Field(default=None, validation_alias="refund_reason")
    gateway_refund_id: str | None
    initiated_at: datetime | None = Field(default=None, validation_alias="requested_at")
    completed_at: datetime | None = Field(default=None, validation_alias="processed_at")
    initiated_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CouponResponse(BaseSchema):
    """
    Standard coupon response for authenticated customers.

    Excluded fields:
    - internal_notes (admin-only)
    - eligible_membership_tiers, applicable_vendor_ids,
      applicable_package_ids, applicable_occasion_categories
      (internal targeting data — exposes business logic to customers)

    remaining_uses is included as a computed field so customers can see
    scarcity without exposing total_usage_limit arithmetic server-side.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    code: str
    title: str
    description: str | None
    coupon_type: CouponType
    applicability: CouponApplicability
    discount_value: Decimal
    max_discount_amount: MoneyAmount | None
    currency: Currency
    min_order_value: MoneyAmount | None
    first_booking_only: bool
    total_usage_limit: int | None
    per_user_limit: int | None
    times_used: int
    is_active: bool
    valid_from: datetime
    valid_until: datetime | None
    is_system_generated: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def remaining_uses(self) -> int | None:
        """Remaining global redemptions; None when there is no usage limit."""
        if self.total_usage_limit is None:
            return None
        return max(0, self.total_usage_limit - self.times_used)

    @computed_field
    @property
    def is_exhausted(self) -> bool:
        """True when the coupon has hit its global usage cap."""
        if self.total_usage_limit is None:
            return False
        return self.times_used >= self.total_usage_limit


class CouponPublicResponse(BaseSchema):
    """
    Minimal coupon details for anonymous / unauthenticated display.

    Used in public marketing pages, banner CTAs, and search results.
    Does not include usage counts, limits, or applicability targeting.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    code: str
    title: str
    description: str | None
    coupon_type: CouponType
    discount_value: Decimal
    max_discount_amount: MoneyAmount | None
    min_order_value: MoneyAmount | None
    valid_until: datetime | None
    is_active: bool


class CouponValidationResponse(BaseSchema):
    """
    Result returned by the coupon validation endpoint.

    When is_valid=False, discount_amount is 0 and error_message explains
    why the coupon cannot be applied. Clients must show error_message
    to the user rather than displaying a generic failure.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    is_valid: bool = Field(description="Whether the coupon applies to this booking")
    discount_amount: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="Computed discount if is_valid=True, else 0.00",
    )
    applied_code: str = Field(description="The coupon code that was validated")
    error_message: str | None = Field(
        default=None,
        description="Reason for rejection when is_valid=False",
    )


class PaymentWebhookResponse(BaseSchema):
    """
    Admin-only response shape for a PaymentWebhook record.

    Excluded fields:
    - payload: raw webhook body (potentially megabytes; use a dedicated
      endpoint to stream the payload when needed for debugging)
    - signature: raw HMAC string (security-sensitive, never expose)
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    payment_id: uuid.UUID | None
    gateway: str
    event_type: str
    is_processed: bool
    processing_error: str | None
    received_at: datetime
    created_at: datetime
    updated_at: datetime
