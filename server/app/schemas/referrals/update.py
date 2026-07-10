"""
Referrals domain — update (PATCH request body) schemas.

All fields are optional; only provided fields are applied.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.referrals.common import ReferralRewardStatus, ReferralStatus


class ReferralUpdate(BaseSchema):
    """
    Partial update payload for a Referral record.

    Used by the referral service on lifecycle transitions (sign-up,
    conversion, reward dispatch) and by admin for fraud review actions.
    """

    referred_user_id: uuid.UUID | None = Field(
        default=None,
        description="Populated when the referred user completes registration",
    )
    referral_status: ReferralStatus | None = Field(
        default=None,
        description="New lifecycle status for the referral",
    )
    signed_up_at: datetime | None = Field(
        default=None,
        description="Timestamp when the referred user signed up",
    )
    converted_at: datetime | None = Field(
        default=None,
        description="Timestamp when the referral triggered a first booking",
    )
    rewarded_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reward was issued to the referrer",
    )
    first_booking_id: uuid.UUID | None = Field(
        default=None,
        description="Booking ID that triggered the conversion event",
    )
    is_fraud_flagged: bool | None = Field(
        default=None,
        description="Mark referral as suspected fraud",
    )
    fraud_reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Reason for flagging this referral as fraud",
    )
    fraud_reviewed_at: datetime | None = Field(
        default=None,
        description="Timestamp when fraud review was completed",
    )
    fraud_reviewed_by_id: uuid.UUID | None = Field(
        default=None,
        description="Admin user ID who performed the fraud review",
    )


class ReferralRewardUpdate(BaseSchema):
    """
    Partial update payload for a ReferralReward record.

    Applied by the payout service as the reward moves through its lifecycle.
    """

    reward_status: ReferralRewardStatus | None = Field(
        default=None,
        description="New status for the reward",
    )
    approved_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reward was approved for payout",
    )
    paid_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reward was actually disbursed",
    )
    expired_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reward expired without being claimed",
    )
    failure_reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Internal reason for payout failure",
    )
