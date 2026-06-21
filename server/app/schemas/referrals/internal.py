"""
Referrals domain — internal / service-layer schemas.

These schemas are NEVER returned directly to API clients. They are used
internally by the service layer, background workers, and admin-only APIs.

Security note: These schemas include fields that are excluded from public
response schemas (ip_address, fraud fields, failure_reason, notes).
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


class ReferralInternal(IDSchema):
    """
    Full internal representation of a Referral including sensitive fields.

    Used by fraud review workflows, admin dashboards, and audit exports.
    Never serialise directly into a public API response.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    referrer_id: uuid.UUID
    referred_user_id: uuid.UUID | None = None
    referral_code: str
    channel: ReferralChannel
    referral_status: ReferralStatus
    signed_up_at: datetime | None = None
    converted_at: datetime | None = None
    rewarded_at: datetime | None = None
    expires_at: datetime | None = None
    first_booking_id: uuid.UUID | None = None

    # Sensitive fields excluded from public responses
    ip_address: str | None = Field(
        default=None,
        description="IP address captured at referral click time",
    )
    is_fraud_flagged: bool = Field(default=False)
    fraud_reason: str | None = None
    fraud_reviewed_at: datetime | None = None
    fraud_reviewed_by_id: uuid.UUID | None = None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ReferralFraudReview(BaseSchema):
    """
    Admin action payload for completing a fraud review on a referral.

    Submitted by an admin after investigating a fraud-flagged referral.
    The service layer applies this and records the reviewing admin's ID.
    """

    fraud_reason: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            "Detailed reason for flagging or clearing the referral. "
            "Set to None when clearing a false-positive flag."
        ),
    )
    fraud_reviewed_at: datetime = Field(
        description="Timestamp of the review decision (should be server time)"
    )
    fraud_reviewed_by_id: uuid.UUID = Field(
        description="Admin user ID who is completing the review"
    )
    is_fraud_flagged: bool = Field(
        description="Final fraud flag state after review; False = cleared"
    )


__all__ = [
    "ReferralInternal",
    "ReferralFraudReview",
]
