"""
Referrals domain — public API response schemas.

Security contract:
  - ip_address is NEVER included (user privacy).
  - Fraud fields (is_fraud_flagged, fraud_reason, fraud_reviewed_at,
    fraud_reviewed_by_id) are NEVER included in public responses.
  - failure_reason and notes on rewards are internal-only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, IDSchema, MoneyAmount
from app.schemas.referrals.common import (
    Currency,
    ReferralChannel,
    ReferralRewardStatus,
    ReferralRewardTrigger,
    ReferralStatus,
    RewardType,
)


class ReferralResponse(IDSchema):
    """
    Public-safe representation of a Referral record.

    Excludes ip_address and all fraud-related fields which are
    restricted to internal/admin views only.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    referrer_id: uuid.UUID = Field(description="User who shared the referral")
    referred_user_id: uuid.UUID | None = Field(
        default=None,
        description="User who registered via this referral (null until sign-up)",
    )
    referral_code: str = Field(description="Referral code that was used")
    channel: ReferralChannel = Field(description="Channel through which it was shared")
    referral_status: ReferralStatus = Field(description="Current lifecycle status")
    signed_up_at: datetime | None = Field(
        default=None,
        description="When the referred user signed up",
    )
    converted_at: datetime | None = Field(
        default=None,
        description="When the referred user made their first booking",
    )
    rewarded_at: datetime | None = Field(
        default=None,
        description="When the reward was issued",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiry deadline for this referral",
    )
    first_booking_id: uuid.UUID | None = Field(
        default=None,
        description="Booking ID that triggered conversion",
    )
    created_at: datetime = Field(description="When this referral was created")


class ReferralRewardResponse(IDSchema):
    """
    Public-safe representation of a ReferralReward.

    failure_reason and notes are internal-only and excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    referral_id: uuid.UUID = Field(description="Parent referral")
    recipient_id: uuid.UUID = Field(description="User receiving the reward")
    reward_trigger: ReferralRewardTrigger = Field(
        description="Event that triggered this reward"
    )
    reward_type: RewardType = Field(description="Category of reward")
    amount: MoneyAmount = Field(description="Reward monetary value")
    currency: Currency = Field(description="Currency of the reward")
    reward_status: ReferralRewardStatus = Field(description="Current payout status")
    approved_at: datetime | None = Field(
        default=None,
        description="When the reward was approved",
    )
    paid_at: datetime | None = Field(
        default=None,
        description="When the reward was disbursed",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Expiry of this reward offer",
    )
    created_at: datetime = Field(description="When the reward record was created")


class ReferralStatsResponse(BaseSchema):
    """
    Aggregated referral performance stats for a referrer.

    Returned by GET /referrals/stats?referrer_id={id} and the
    referrer's dashboard summary endpoint.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    referrer_id: uuid.UUID = Field(description="User whose stats are shown")
    total_referrals: int = Field(ge=0, description="Total referrals initiated")
    signed_up_count: int = Field(
        ge=0,
        description="Referrals where the referred user signed up",
    )
    converted_count: int = Field(
        ge=0,
        description="Referrals that reached first-booking conversion",
    )
    rewarded_count: int = Field(
        ge=0,
        description="Referrals for which a reward was issued",
    )
    total_earned: MoneyAmount = Field(
        description="Cumulative reward amount earned across all paid referrals"
    )
