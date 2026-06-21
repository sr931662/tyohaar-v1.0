"""
Memberships domain — internal / admin-only schemas.

Exposes full plan configuration and subscription details including
payment references and audit fields not visible to end-users.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.schemas.memberships.response import MembershipPlanResponse, UserMembershipResponse

__all__ = [
    "MembershipPlanInternal",
    "UserMembershipInternal",
]


class MembershipPlanInternal(MembershipPlanResponse):
    """
    Admin view of a membership plan.

    Includes full configuration metadata and soft-delete state.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp; None means plan record is live.",
    )
    created_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin who created this plan.",
    )
    last_modified_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin who last modified this plan.",
    )
    active_subscriber_count: int | None = Field(
        default=None,
        description="Number of users currently on this plan (populated by admin queries).",
    )


class UserMembershipInternal(UserMembershipResponse):
    """
    Admin and finance view of a user membership subscription.

    Includes the payment gateway reference for reconciliation.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_reference: str | None = Field(
        default=None,
        max_length=200,
        description="Gateway transaction ID used for payment reconciliation.",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp.",
    )
