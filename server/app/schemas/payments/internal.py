"""
Internal-only schemas for the payments domain.

These schemas are NEVER serialised to public API responses. They are used
exclusively within the service and repository layers, background jobs,
webhook processors, and admin-only endpoints.

WARNING:
- PaymentInternal includes gateway_signature (HMAC secret — internal only).
- PaymentWebhookInternal includes payload (raw webhook body) and
  signature (HMAC string) — both must remain server-side.
- CouponInternal includes internal_notes and all eligibility targeting
  fields excluded from the public CouponResponse.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.schemas.payments.response import (
    CouponResponse,
    PaymentResponse,
    PaymentWebhookResponse,
)
from app.schemas.payments.common import PaymentGatewayEnum
from app.models.enums import CouponApplicability, CouponType, Currency


__all__ = [
    "PaymentInternal",
    "PaymentWebhookInternal",
    "CouponInternal",
]


class PaymentInternal(PaymentResponse):
    """
    Full payment record including the gateway HMAC signature.

    Use ONLY in webhook verification handlers and internal audit services.
    Never pass to any serialiser that might return data to a client.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    gateway_signature: str | None = Field(
        default=None,
        description=(
            "HMAC-SHA256 signature received from the gateway webhook. "
            "Used to verify webhook authenticity — NEVER expose externally."
        ),
    )


class PaymentWebhookInternal(PaymentWebhookResponse):
    """
    Full webhook record including raw payload and HMAC signature.

    Use ONLY in webhook ingestion pipelines and internal debugging tools.
    payload can be arbitrarily large; fetch on-demand rather than listing.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payload: dict = Field(
        description=(
            "Raw webhook payload as received from the gateway. "
            "May be large; never include in list responses."
        )
    )
    signature: str | None = Field(
        default=None,
        description=(
            "Raw HMAC signature string for replay verification — "
            "NEVER expose externally."
        ),
    )


class CouponInternal(CouponResponse):
    """
    Full coupon record including admin-only and eligibility targeting fields.

    Extends the authenticated CouponResponse with data that must remain
    server-side. Use in admin panels and the coupon eligibility service.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Admin-only notes
    internal_notes: str | None = Field(
        default=None,
        description="Admin-only notes — never expose to customers",
    )

    # Eligibility targeting — internal only
    eligible_membership_tiers: list[str] | None = Field(
        default=None,
        description=(
            "Membership tier names that can use this coupon. "
            "Internal — exposes pricing strategy if leaked."
        ),
    )
    applicable_vendor_ids: list[uuid.UUID] | None = Field(
        default=None,
        description=(
            "Vendor UUIDs this coupon targets. "
            "Internal — reveals vendor relationships if leaked."
        ),
    )
    applicable_package_ids: list[uuid.UUID] | None = Field(
        default=None,
        description=(
            "Package UUIDs this coupon applies to. "
            "Internal — reveals pricing segmentation if leaked."
        ),
    )
    applicable_occasion_categories: list[str] | None = Field(
        default=None,
        description="Occasion categories this coupon targets (internal targeting).",
    )
    applicable_occasion_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific occasion UUIDs this coupon targets (internal targeting).",
    )
    repeat_customers_only: bool = Field(default=False)
    referral_users_only: bool = Field(default=False)
    eligible_customer_group_ids: list[uuid.UUID] | None = Field(
        default=None, description="Reserved for future use"
    )
    min_package_value: MoneyAmount | None = Field(default=None)
    max_uses_per_day: int | None = Field(default=None)
    max_uses_per_vendor: int | None = Field(default=None, description="Reserved for future use")
    max_uses_per_package: int | None = Field(default=None, description="Reserved for future use")
    condition_rules: dict | None = Field(
        default=None,
        description="Condition tree for date/behavior-based automatic discounts",
    )
    deactivated_at: datetime | None = Field(
        default=None,
        description="UTC datetime when the coupon was deactivated",
    )
    created_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin UUID who created this coupon (None = system-generated)",
    )
