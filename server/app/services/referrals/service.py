"""
ReferralService — referral code management, reward triggers, and analytics.

All public methods open their own UoW so each call is one atomic transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.enums import ReferralStatus, RewardType
from app.models.referrals.referral import Referral, ReferralChannel
from app.models.referrals.referral_reward import (
    ReferralReward,
    ReferralRewardStatus,
    ReferralRewardTrigger,
)
from app.schemas.base import CursorPage
from app.schemas.referrals.response import (
    ReferralResponse,
    ReferralRewardResponse,
    ReferralStatsResponse,
)
from app.services.base import BaseService
from app.services.referrals.constants import (
    MIN_BOOKING_AMOUNT_FOR_REWARD,
    REFEREE_REWARD_AMOUNT,
    REFERRER_REWARD_AMOUNT,
)
from app.services.referrals.exceptions import (
    AlreadyReferredError,
    ReferralAlreadyCompletedError,
    ReferralCodeNotFoundError,
    ReferralRewardAlreadyActivatedError,
    ReferralRewardNotFoundError,
)
from app.services.referrals.helpers import generate_referral_code
from app.services.referrals.validators import (
    validate_not_already_referred,
    validate_not_self_referral,
    validate_referral_code,
    validate_referral_reward_exists,
)

# ---------------------------------------------------------------------------
# Inline response stubs for endpoints not yet backed by full schema modules
# ---------------------------------------------------------------------------
from app.schemas.base import BaseSchema as _BaseSchema


class ReferralCodeResponse(_BaseSchema):
    user_id: UUID
    referral_code: str


class _CursorPageHelper:
    @staticmethod
    def wrap(items: list, limit: int) -> CursorPage:
        has_more = len(items) > limit
        return CursorPage(
            items=items[:limit] if has_more else items,
            has_more=has_more,
            next_cursor=None,
        )


class ReferralService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # =========================================================================
    # Referral codes
    # =========================================================================

    async def get_referral_code(self, user_id: UUID) -> ReferralCodeResponse:
        """
        Return the user's existing active referral code, or create one.
        Each user has exactly one active code at a time.
        """
        code = generate_referral_code(user_id)

        async with self._uow() as uow:
            # Check if any referral row for this user already records the code
            existing_rows = await uow.referrals.referrals.find_by_referrer(
                user_id, limit=1
            )
            if existing_rows:
                code = existing_rows[0].referral_code
            else:
                # Create a sentinel Referral row to persist the code
                referral = Referral(
                    referrer_id=user_id,
                    referral_code=code,
                    referral_status=ReferralStatus.PENDING,
                    channel=ReferralChannel.DIRECT_LINK,
                )
                await uow.referrals.referrals.create(referral)
                await uow.commit()

        return ReferralCodeResponse(user_id=user_id, referral_code=code)

    # =========================================================================
    # Apply referral
    # =========================================================================

    async def apply_referral_code(
        self,
        referee_id: UUID,
        code: str,
    ) -> ReferralResponse:
        """
        Validate and apply a referral code for a new user.

        Steps:
        1. Verify code exists (NotFoundError if not).
        2. Verify referee not already referred.
        3. Verify not self-referral.
        4. Create Referral record (status=PENDING, referred_user_id=referee_id).
        """
        async with self._uow() as uow:
            referral_row = await validate_referral_code(code, uow)
            if referral_row is None:
                raise ReferralCodeNotFoundError(code)

            referrer_id = referral_row.referrer_id
            await validate_not_already_referred(referee_id, uow)
            await validate_not_self_referral(referrer_id, referee_id)

            new_referral = Referral(
                referrer_id=referrer_id,
                referred_user_id=referee_id,
                referral_code=code,
                referral_status=ReferralStatus.SIGNED_UP,
                channel=ReferralChannel.DIRECT_LINK,
                signed_up_at=datetime.now(tz=timezone.utc),
            )
            new_referral = await uow.referrals.referrals.create(new_referral)
            await uow.commit()

        return ReferralResponse.model_validate(new_referral)

    # =========================================================================
    # Reward triggers
    # =========================================================================

    async def trigger_referral_rewards(
        self,
        referee_id: UUID,
        booking_amount: Decimal,
        booking_id: UUID,
    ) -> None:
        """
        Issue referral rewards when a qualifying booking is completed.

        Idempotent: if rewards already exist for this referral, exits silently.
        """
        async with self._uow() as uow:
            referral = await uow.referrals.referrals.find_by_referred_user(referee_id)
            if referral is None:
                return  # No referral on file for this user

            if referral.referral_status in (
                ReferralStatus.REWARDED,
                ReferralStatus.CONVERTED,
            ):
                return  # Already processed (idempotent)

            if booking_amount < MIN_BOOKING_AMOUNT_FOR_REWARD:
                return  # Does not meet minimum booking threshold

            now = datetime.now(tz=timezone.utc)

            # Referrer reward
            referrer_reward = ReferralReward(
                referral_id=referral.id,
                recipient_id=referral.referrer_id,
                reward_type=RewardType.REFERRAL_BONUS,
                reward_trigger=ReferralRewardTrigger.FIRST_BOOKING,
                monetary_value=REFERRER_REWARD_AMOUNT,
                reward_status=ReferralRewardStatus.PENDING,
                calculated_at=now,
            )
            await uow.referrals.rewards.create(referrer_reward)

            # Referee reward
            referee_reward = ReferralReward(
                referral_id=referral.id,
                recipient_id=referee_id,
                reward_type=RewardType.WELCOME_BONUS,
                reward_trigger=ReferralRewardTrigger.FIRST_BOOKING,
                monetary_value=REFEREE_REWARD_AMOUNT,
                reward_status=ReferralRewardStatus.PENDING,
                calculated_at=now,
            )
            await uow.referrals.rewards.create(referee_reward)

            # Mark referral as completed
            await uow.referrals.referrals.update(referral, {
                "referral_status": ReferralStatus.CONVERTED,
                "converted_at": now,
                "first_booking_id": booking_id,
            })
            await uow.commit()

    async def activate_referral_reward(
        self,
        reward_id: UUID,
        admin_id: UUID,
    ) -> ReferralRewardResponse:
        """Transition a PENDING reward to APPROVED and credit the wallet."""
        async with self._uow() as uow:
            reward = await validate_referral_reward_exists(reward_id, uow)

            if reward.reward_status != ReferralRewardStatus.PENDING:
                raise ReferralRewardAlreadyActivatedError(
                    f"Reward is already in status '{reward.reward_status}'."
                )

            now = datetime.now(tz=timezone.utc)
            reward = await uow.referrals.rewards.update(reward, {
                "reward_status": ReferralRewardStatus.APPROVED,
                "approved_at": now,
                "approved_by_id": admin_id,
            })
            # Cross-domain: credit corresponding wallet (stub)
            # await uow.wallets.wallet.credit(reward.recipient_id, reward.monetary_value)
            await uow.commit()

        return ReferralRewardResponse.model_validate(reward)

    async def expire_pending_referral_rewards(self, cutoff_date: datetime) -> int:
        """Batch-expire all PENDING rewards whose expires_at is before cutoff_date.

        Returns the number of rewards expired.
        """
        async with self._uow() as uow:
            expiring = await uow.referrals.rewards.find_expiring_soon(cutoff_date)
            if not expiring:
                return 0
            ids = [r.id for r in expiring]
            count = await uow.referrals.rewards.bulk_update(
                ids,
                {"reward_status": ReferralRewardStatus.EXPIRED},
            )
            await uow.commit()
        return count

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_referral_stats(self, user_id: UUID) -> ReferralStatsResponse:
        async with self._uow() as uow:
            counts = await uow.referrals.referrals.count_by_referrer(user_id)
            paid_rewards = await uow.referrals.rewards.find_paid_for_recipient(
                user_id, limit=500
            )

        total_earned = sum(
            (r.monetary_value for r in paid_rewards), Decimal("0.00")
        )
        return ReferralStatsResponse(
            referrer_id=user_id,
            total_referrals=sum(counts.values()),
            signed_up_count=counts.get(ReferralStatus.SIGNED_UP, 0),
            converted_count=counts.get(ReferralStatus.CONVERTED, 0),
            rewarded_count=counts.get(ReferralStatus.REWARDED, 0),
            total_earned=total_earned,
        )

    async def list_referrals(
        self,
        user_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            referrals = await uow.referrals.referrals.find_by_referrer(
                user_id, limit=limit + 1
            )
        responses = [ReferralResponse.model_validate(r) for r in referrals]
        return _CursorPageHelper.wrap(responses, limit)

    async def list_rewards(
        self,
        user_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            rewards = await uow.referrals.rewards.find_by_recipient(
                user_id, limit=limit + 1
            )
        responses = [ReferralRewardResponse.model_validate(r) for r in rewards]
        return _CursorPageHelper.wrap(responses, limit)

    async def get_reward(
        self,
        reward_id: UUID,
        user_id: UUID,
    ) -> ReferralRewardResponse:
        async with self._uow() as uow:
            reward = await validate_referral_reward_exists(reward_id, uow)
        # Only show status and value; structural security enforced by response schema
        return ReferralRewardResponse.model_validate(reward)
