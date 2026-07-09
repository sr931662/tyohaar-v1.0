"""
Referral milestone schemas — admin-configurable "every N referrals unlocks
a discount on the next M plans" rewards.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema, MoneyAmount, Percentage

__all__ = [
    "ReferralMilestoneRuleCreate",
    "ReferralMilestoneRuleUpdate",
    "ReferralMilestoneRuleResponse",
    "ReferralMilestoneGrantResponse",
]


class ReferralMilestoneRuleCreate(BaseSchema):
    """Admin-only. Creating a new rule deactivates any currently-active one."""

    referrals_required: int = Field(gt=0, description="For every N successful referrals, unlock the reward.")
    discount_percentage: Percentage = Field(description="Discount % on qualifying bookings once unlocked.")
    applicable_plan_count: int = Field(gt=0, description="Number of future bookings the discount applies to.")
    min_plan_price: MoneyAmount = Field(description="Minimum booking subtotal required for the discount to apply.")
    is_active: bool = Field(default=True)


class ReferralMilestoneRuleUpdate(BaseSchema):
    referrals_required: int | None = Field(default=None, gt=0)
    discount_percentage: Percentage | None = None
    applicable_plan_count: int | None = Field(default=None, gt=0)
    min_plan_price: MoneyAmount | None = None
    is_active: bool | None = None


class ReferralMilestoneRuleResponse(BaseSchema):
    id: uuid.UUID
    referrals_required: int
    discount_percentage: Decimal
    applicable_plan_count: int
    min_plan_price: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReferralMilestoneGrantResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    rule_id: uuid.UUID
    discount_percentage: Decimal
    min_plan_price: Decimal
    plans_remaining: int
    created_at: datetime
