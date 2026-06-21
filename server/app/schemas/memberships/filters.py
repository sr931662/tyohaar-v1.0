"""
Memberships domain — filter query parameter schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import (
    MembershipBillingCycle,
    MembershipStatus,
    MembershipTier,
)
from app.schemas.base import BaseSchema

__all__ = [
    "MembershipPlanFilters",
    "UserMembershipFilters",
]


class MembershipPlanFilters(BaseSchema):
    """
    Filter parameters for the membership plan catalog endpoint.

    Typically used by the admin plan listing; the public endpoint
    always filters is_active=True at the router level.
    """

    tier: MembershipTier | None = Field(
        default=None,
        description="Filter plans by membership tier.",
    )
    is_active: bool | None = Field(
        default=None,
        description="True = only active plans; False = only inactive; None = all.",
    )


class UserMembershipFilters(BaseSchema):
    """
    Filter parameters for user membership history and admin subscription management.

    from_date / to_date filter on the expires_at column, enabling queries like
    'memberships expiring this month' for renewal campaign targeting.
    """

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter memberships belonging to a specific user.",
    )
    plan_id: uuid.UUID | None = Field(
        default=None,
        description="Filter subscriptions to a specific plan.",
    )
    tier: MembershipTier | None = Field(
        default=None,
        description="Filter by denormalized tier value.",
    )
    status: MembershipStatus | None = Field(
        default=None,
        description="Filter by membership lifecycle status.",
    )
    billing_cycle: MembershipBillingCycle | None = Field(
        default=None,
        description="Filter by billing cadence.",
    )
    auto_renew: bool | None = Field(
        default=None,
        description="Filter by auto-renewal preference.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Include only memberships expiring at or after this timestamp.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Include only memberships expiring at or before this timestamp.",
    )
