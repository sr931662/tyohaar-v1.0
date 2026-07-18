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
    CouponAdminStatus,
    CouponApplicability,
    CouponEffectiveStatus,
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
    "AppliedDiscountItem",
    "DiscountEvaluationResponse",
    "TopCouponStat",
    "DiscountAnalyticsOverview",
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
    code: str | None
    is_automatic: bool
    title: str
    public_offer_title: str | None
    description: str | None
    terms_and_conditions: str | None
    coupon_type: CouponType
    applicability: CouponApplicability
    discount_value: Decimal
    max_discount_amount: MoneyAmount | None
    currency: Currency
    priority: int
    is_stackable: bool
    admin_status: CouponAdminStatus
    banner_image_url: str | None
    theme_color_hex: str | None
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

    @computed_field
    @property
    def effective_status(self) -> CouponEffectiveStatus:
        """Fully-derived status (draft/scheduled/active/paused/expired/archived)."""
        if self.admin_status == CouponAdminStatus.ARCHIVED:
            return CouponEffectiveStatus.ARCHIVED
        if self.admin_status == CouponAdminStatus.DRAFT:
            return CouponEffectiveStatus.DRAFT
        if self.admin_status == CouponAdminStatus.PAUSED:
            return CouponEffectiveStatus.PAUSED
        from datetime import timezone as _timezone
        now = datetime.now(tz=_timezone.utc)
        if self.valid_from > now:
            return CouponEffectiveStatus.SCHEDULED
        if self.valid_until is not None and self.valid_until < now:
            return CouponEffectiveStatus.EXPIRED
        return CouponEffectiveStatus.ACTIVE


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


class AppliedDiscountItem(BaseSchema):
    """One discount included in a DiscountEvaluationResponse's applied list."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    coupon_id: uuid.UUID
    title: str
    public_offer_title: str | None = None
    code: str | None = Field(default=None, description="Null for automatic discounts")
    coupon_type: CouponType
    discount_amount: MoneyAmount


class DiscountEvaluationResponse(BaseSchema):
    """
    Full itemized result from DiscountEngine.evaluate — the single shape
    returned by both the checkout-time preview endpoint and used internally
    by create_booking. All discount calculation happens server-side; clients
    only ever display this result, never compute discounts themselves.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    original_amount: MoneyAmount
    applied_discounts: list[AppliedDiscountItem] = Field(default_factory=list)
    total_discount: MoneyAmount = Field(default=Decimal("0.00"))
    final_amount: MoneyAmount
    coupon_error: str | None = Field(
        default=None,
        description="If a coupon_code was supplied but rejected, the human-readable reason",
    )


class TopCouponStat(BaseSchema):
    """One row in the discount analytics 'top performing' leaderboard."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    coupon_id: uuid.UUID
    title: str
    code: str | None
    times_used: int
    revenue_generated: MoneyAmount = Field(default=Decimal("0.00"))


class DiscountAnalyticsOverview(BaseSchema):
    """
    Admin discount analytics summary.

    conversion_rate is computed as (bookings with an applied discount whose
    payment reached COMPLETED) / (all bookings with an applied discount) —
    the closest honest proxy available without a separate impressions/
    evaluation-log table (evaluate() is read-only and isn't itself logged).
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_discounts: int
    draft_count: int
    scheduled_count: int
    active_count: int
    paused_count: int
    expired_count: int
    archived_count: int

    total_times_used: int
    total_revenue_generated: MoneyAmount = Field(default=Decimal("0.00"))
    total_revenue_lost: MoneyAmount = Field(default=Decimal("0.00"))
    conversion_rate: float = Field(default=0.0, description="Percentage, 0-100")

    top_coupons: list[TopCouponStat] = Field(default_factory=list)


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
