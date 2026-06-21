"""
Memberships domain — create (input) schemas.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.models.enums import (
    Currency,
    MembershipBillingCycle,
    MembershipTier,
)
from app.schemas.base import BaseSchema, MoneyAmount, Percentage

__all__ = [
    "MembershipPlanCreate",
    "UserMembershipCreate",
]


class MembershipPlanCreate(BaseSchema):
    """
    Admin-only input schema for creating a membership plan.

    Slug must be unique across all plans and is used in URLs and
    deep links. Tier must not already have an active plan unless
    the existing plan is being superseded (enforced in service layer).
    """

    tier: MembershipTier
    name: str = Field(max_length=100, description="Display name, e.g. 'Gold Member'.")
    slug: str = Field(
        max_length=50,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe lowercase slug, e.g. 'gold-annual'.",
    )
    tagline: str | None = Field(
        default=None,
        max_length=200,
        description="Short marketing tagline displayed under plan name.",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Full plan description shown on the membership details page.",
    )
    monthly_price: MoneyAmount = Field(description="Price per month in plan currency.")
    yearly_price: MoneyAmount = Field(description="Price per year (typically discounted).")
    validity_days: int | None = Field(
        default=None,
        ge=1,
        description="Fixed validity window in days. None means perpetual until cancelled.",
    )
    cashback_percentage: Percentage = Field(
        default=Decimal("0.00"),
        description="Cashback rate on eligible bookings (0–100).",
    )
    discount_percentage: Percentage = Field(
        default=Decimal("0.00"),
        description="Flat discount rate on eligible packages (0–100).",
    )
    reward_multiplier: Decimal = Field(
        default=Decimal("1.00"),
        ge=Decimal("1.00"),
        decimal_places=2,
        description="Loyalty point multiplier; 2.0 means double points on all bookings.",
    )
    wallet_bonus: MoneyAmount = Field(
        default=Decimal("0.00"),
        description="One-time wallet credit granted on plan activation.",
    )
    free_invitations_count: int = Field(
        default=0,
        ge=0,
        description="Number of free digital invitation designs included.",
    )
    priority_booking: bool = Field(
        default=False,
        description="Whether members get priority access to high-demand time slots.",
    )
    has_exclusive_packages: bool = Field(
        default=False,
        description="Whether tier unlocks exclusive packages not available to free users.",
    )
    cancellation_protection: bool = Field(
        default=False,
        description="Whether tier includes free cancellation protection on bookings.",
    )
    customer_support_priority: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Support queue priority: 1=standard, 2=priority, 3=dedicated.",
    )
    can_upgrade_to_tier: MembershipTier | None = Field(
        default=None,
        description="Which tier this plan can be directly upgraded to.",
    )
    can_downgrade_to_tier: MembershipTier | None = Field(
        default=None,
        description="Which tier this plan can be downgraded to.",
    )
    benefits: dict[str, Any] | None = Field(
        default=None,
        description="Flexible JSONB map of additional benefit definitions.",
    )
    is_active: bool = Field(
        default=True,
        description="Inactive plans are not shown in the plan selection flow.",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        le=32767,
        description="Ascending sort order in plan comparison grids.",
    )

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower().strip()

    @model_validator(mode="after")
    def yearly_price_not_more_than_12x_monthly(self) -> "MembershipPlanCreate":
        if self.yearly_price > self.monthly_price * 12:
            raise ValueError(
                "yearly_price should not exceed 12x monthly_price — check for data entry error."
            )
        return self


class UserMembershipCreate(BaseSchema):
    """
    Input schema for subscribing a user to a membership plan.

    Called by the membership checkout service after payment confirmation.
    started_at and expires_at are computed by the service from billing_cycle
    and plan.validity_days.
    """

    user_id: uuid.UUID = Field(description="User being subscribed.")
    plan_id: uuid.UUID = Field(description="MembershipPlan UUID being purchased.")
    billing_cycle: MembershipBillingCycle = Field(
        description="Billing cadence selected at checkout.",
    )
    auto_renew: bool = Field(
        default=True,
        description="Whether to auto-renew at the end of the billing period.",
    )


# Alias consumed by the memberships controller
SubscribeCreate = UserMembershipCreate
