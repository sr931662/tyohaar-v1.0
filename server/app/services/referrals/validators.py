"""Referrals domain — async validator helpers that operate inside a UnitOfWork."""

from __future__ import annotations

import uuid

from app.models.referrals.referral import Referral
from app.models.referrals.referral_reward import ReferralReward
from app.repositories.unit_of_work import UnitOfWork
from app.services.referrals.exceptions import (
    AlreadyReferredError,
    ReferralRewardNotFoundError,
    SelfReferralError,
)


async def validate_referral_code(
    code: str,
    uow: UnitOfWork,
) -> Referral | None:
    """Return the active Referral for *code*, or None if not found.

    Does NOT raise — callers decide how to handle a missing code.
    """
    return await uow.referrals.referrals.find_latest_by_code(code)


async def validate_not_already_referred(
    referee_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    """Raise AlreadyReferredError if this user has already been referred."""
    existing = await uow.referrals.referrals.find_by_referred_user(referee_id)
    if existing is not None:
        raise AlreadyReferredError(
            "User has already been referred and cannot use another referral code."
        )


async def validate_not_self_referral(
    referrer_id: uuid.UUID,
    referee_id: uuid.UUID,
) -> None:
    """Raise SelfReferralError when referrer and referee are the same user."""
    if referrer_id == referee_id:
        raise SelfReferralError()


async def validate_referral_reward_exists(
    reward_id: uuid.UUID,
    uow: UnitOfWork,
) -> ReferralReward:
    """Fetch a ReferralReward by ID or raise ReferralRewardNotFoundError."""
    reward = await uow.referrals.rewards.get_by_id(reward_id)
    if reward is None:
        raise ReferralRewardNotFoundError(str(reward_id))
    return reward
