"""
Referrals domain — query filter schemas.

Used as query-parameter models on list endpoints. All fields are optional;
absent fields are ignored by the repository layer.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.referrals.common import (
    ReferralChannel,
    ReferralRewardStatus,
    ReferralRewardTrigger,
    ReferralStatus,
    RewardType,
)


class ReferralFilters(BaseSchema):
    """
    Filter parameters for the referral list endpoint.

    GET /referrals?referrer_id=...&channel=link&referral_status=converted
    """

    referrer_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by the user who referred others",
    )
    referred_user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by the user who signed up via a referral",
    )
    referral_code: str | None = Field(
        default=None,
        max_length=20,
        description="Exact referral code match",
    )
    channel: ReferralChannel | None = Field(
        default=None,
        description="Filter by share channel",
    )
    referral_status: ReferralStatus | None = Field(
        default=None,
        description="Filter by lifecycle status",
    )
    is_fraud_flagged: bool | None = Field(
        default=None,
        description="Filter fraud-flagged referrals (admin use)",
    )
    from_date: date | None = Field(
        default=None,
        description="Inclusive start date filter on created_at",
    )
    to_date: date | None = Field(
        default=None,
        description="Inclusive end date filter on created_at",
    )


class ReferralRewardFilters(BaseSchema):
    """
    Filter parameters for the referral rewards list endpoint.

    GET /referrals/rewards?recipient_id=...&reward_status=paid
    """

    referral_id: uuid.UUID | None = Field(
        default=None,
        description="Filter rewards belonging to a specific referral",
    )
    recipient_id: uuid.UUID | None = Field(
        default=None,
        description="Filter rewards for a specific recipient user",
    )
    reward_trigger: ReferralRewardTrigger | None = Field(
        default=None,
        description="Filter by triggering business event",
    )
    reward_type: RewardType | None = Field(
        default=None,
        description="Filter by reward category",
    )
    reward_status: ReferralRewardStatus | None = Field(
        default=None,
        description="Filter by current payout status",
    )
    from_date: date | None = Field(
        default=None,
        description="Inclusive start date filter on created_at",
    )
    to_date: date | None = Field(
        default=None,
        description="Inclusive end date filter on created_at",
    )
