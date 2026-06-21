"""
Referrals domain — referral lifecycle, fraud prevention, and reward tracking.

Import order follows dependency graph (leaf models first):
  Referral (no deps within referrals)
  → ReferralReward (references Referral)
"""

from app.models.referrals.referral import Referral, ReferralChannel
from app.models.referrals.referral_reward import (
    ReferralReward,
    ReferralRewardStatus,
    ReferralRewardTrigger,
)

__all__ = [
    # Models
    "Referral",
    "ReferralReward",
    # Local enums (move to enums.py in next enums update)
    "ReferralChannel",
    "ReferralRewardStatus",
    "ReferralRewardTrigger",
]
