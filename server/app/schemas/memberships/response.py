"""
Memberships domain — response (output) schemas.

Security: internal_notes and deleted_at are never exposed here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, computed_field

from app.models.enums import (
    MembershipBillingCycle,
    MembershipStatus,
    MembershipTier,
)
from app.schemas.base import BaseSchema, MoneyAmount, Percentage

__all__ = [
    "MembershipPlanResponse",
    "UserMembershipResponse",
]


class MembershipPlanResponse(BaseSchema):
    """
    Public membership plan representation for the plan listing and detail endpoints.

    The `benefits` field is returned as-is from the JSONB column; clients
    should use the PlanBenefitSchema for structured rendering.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    tier: MembershipTier
    name: str
    slug: str
    tagline: str | None = None
    description: str | None = None
    monthly_price: Decimal = Field(decimal_places=2)
    yearly_price: Decimal = Field(decimal_places=2)
    validity_days: int | None = None
    cashback_percentage: Decimal = Field(decimal_places=2)
    discount_percentage: Decimal = Field(decimal_places=2)
    reward_multiplier: Decimal = Field(decimal_places=2)
    wallet_bonus: Decimal = Field(decimal_places=2)
    free_invitations_count: int
    priority_booking: bool
    has_exclusive_packages: bool
    cancellation_protection: bool
    customer_support_priority: int
    can_upgrade_to_tier: MembershipTier | None = None
    can_downgrade_to_tier: MembershipTier | None = None
    benefits: dict[str, Any] | None = None
    is_active: bool
    display_order: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_savings(self) -> Decimal:
        """How much a customer saves by paying yearly vs monthly."""
        return (self.monthly_price * 12) - self.yearly_price


class UserMembershipResponse(BaseSchema):
    """
    Customer-facing view of an active or historical membership subscription.

    Field names mirror the UserMembership model directly (membership_status,
    activated_at, ...) except `tier`, which is denormalized from the related
    MembershipPlan since UserMembership itself has no tier column. Built via
    MembershipService._to_membership_response() — never via a bare
    model_validate(membership), since `tier` cannot come from attribute access
    alone and the `plan` relationship is lazy="noload" (unsafe to touch under
    the async engine without an explicit eager-load).
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    tier: MembershipTier | None = None
    billing_cycle: MembershipBillingCycle
    membership_status: MembershipStatus
    is_lifetime: bool
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    next_renewal_at: datetime | None = None
    grace_period_until: datetime | None = None
    auto_renew: bool
    renewal_count: int
    payment_id: uuid.UUID | None = None
    upgraded_from_plan_id: uuid.UUID | None = None
    upgrade_reason: str | None = None
    cancellation_reason: str | None = None
    cancellation_notes: str | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        """Convenience flag: True when status is ACTIVE or GRACE_PERIOD."""
        from app.models.enums import MembershipStatus as MS
        return self.membership_status in (MS.ACTIVE, MS.GRACE_PERIOD)


# Alias consumed by the memberships controller
MembershipResponse = UserMembershipResponse
