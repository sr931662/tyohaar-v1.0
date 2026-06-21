"""
Memberships domain — update (patch) schemas.

All fields are Optional for partial PATCH semantics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.models.enums import (
    MembershipBillingCycle,
    MembershipStatus,
    MembershipTier,
)
from app.schemas.base import BaseSchema, MoneyAmount, Percentage

__all__ = [
    "MembershipPlanUpdate",
    "UserMembershipUpdate",
]


class MembershipPlanUpdate(BaseSchema):
    """
    Admin-only partial update schema for membership plan configuration.

    Slug is intentionally excluded from updates — changing a slug would
    break bookmarked URLs and existing deep links. Create a new plan instead.
    """

    name: str | None = Field(default=None, max_length=100)
    tagline: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    monthly_price: MoneyAmount | None = None
    yearly_price: MoneyAmount | None = None
    validity_days: int | None = Field(default=None, ge=1)
    cashback_percentage: Percentage | None = None
    discount_percentage: Percentage | None = None
    reward_multiplier: Decimal | None = Field(
        default=None,
        ge=Decimal("1.00"),
        decimal_places=2,
    )
    wallet_bonus: MoneyAmount | None = None
    free_invitations_count: int | None = Field(default=None, ge=0)
    priority_booking: bool | None = None
    has_exclusive_packages: bool | None = None
    cancellation_protection: bool | None = None
    customer_support_priority: int | None = Field(default=None, ge=1, le=3)
    can_upgrade_to_tier: MembershipTier | None = None
    can_downgrade_to_tier: MembershipTier | None = None
    benefits: dict[str, Any] | None = None
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0, le=32767)


class UserMembershipUpdate(BaseSchema):
    """
    Partial update schema for a user's membership subscription.

    Used by the membership service for renewals, cancellations, and
    admin adjustments. Financial fields are managed by the payment service.
    """

    status: MembershipStatus | None = Field(
        default=None,
        description="New lifecycle state, e.g. CANCELLED, PAUSED, GRACE_PERIOD.",
    )
    auto_renew: bool | None = Field(
        default=None,
        description="Toggle auto-renewal preference.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Override the expiry timestamp (admin use only).",
    )
    cancelled_at: datetime | None = Field(
        default=None,
        description="When cancellation was requested.",
    )
    cancellation_reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Customer-supplied or admin-supplied cancellation reason.",
    )
    invitations_remaining: int | None = Field(
        default=None,
        ge=0,
        description="Adjusted count of remaining free invitation credits.",
    )
