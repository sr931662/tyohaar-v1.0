"""
Referrals domain — shared types, enum re-exports, and nested schemas.

Import from here instead of importing enums or model files individually
in other referrals schema modules.
"""

from __future__ import annotations

import enum

from app.models.enums import Currency, ReferralStatus, RewardType
from app.schemas.base import BaseSchema, MoneyAmount

# ── Local enums (mirrors app.models.referrals.referral / referral_reward) ─────


class ReferralChannel(str, enum.Enum):
    """Channel through which a referral was initiated."""

    LINK = "link"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SOCIAL = "social"
    VERBAL = "verbal"
    OTHER = "other"


class ReferralRewardStatus(str, enum.Enum):
    """Lifecycle state of a referral reward payout."""

    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReferralRewardTrigger(str, enum.Enum):
    """Business event that triggers a referral reward."""

    SIGNUP = "signup"
    FIRST_BOOKING = "first_booking"
    FIRST_PAYMENT = "first_payment"
    MILESTONE = "milestone"


__all__ = [
    # local enums
    "ReferralChannel",
    "ReferralRewardStatus",
    "ReferralRewardTrigger",
    # re-exported from app.models.enums
    "ReferralStatus",
    "RewardType",
    "Currency",
]
