"""Referrals domain — service-layer exceptions."""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)


class ReferralCodeNotFoundError(NotFoundError):
    def __init__(self, code: str | None = None) -> None:
        super().__init__("ReferralCode", code)


class SelfReferralError(BusinessRuleError):
    default_message = "You cannot refer yourself."


class AlreadyReferredError(ConflictError):
    default_message = "This user has already been referred by another referral code."


class ReferralRewardNotFoundError(NotFoundError):
    def __init__(self, reward_id: str | None = None) -> None:
        super().__init__("ReferralReward", reward_id)


class ReferralRewardAlreadyActivatedError(ConflictError):
    default_message = "This referral reward has already been activated."


class ReferralAlreadyCompletedError(ConflictError):
    default_message = "This referral has already been completed."


class ReferralMilestoneRuleNotFoundError(NotFoundError):
    def __init__(self, rule_id: str | None = None) -> None:
        super().__init__("ReferralMilestoneRule", rule_id)
