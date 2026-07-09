"""
Referral repository — Referral and ReferralReward.

Two sub-repositories handle the referral domain. ReferralReward is effectively
immutable once PAID — mutations are limited to status transitions and cancellation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ReferralStatus
from app.models.referrals.referral import Referral, ReferralChannel
from app.models.referrals.referral_milestone import ReferralMilestoneGrant, ReferralMilestoneRule
from app.models.referrals.referral_reward import ReferralReward, ReferralRewardStatus, ReferralRewardTrigger
from app.repositories.base import BaseRepository


class ReferralRepository(BaseRepository[Referral]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Referral)

    # ── Lookup ────────────────────────────────────────────────────────────────

    async def find_by_code(
        self,
        referral_code: str,
        *,
        include_fraud: bool = False,
    ) -> list[Referral]:
        """Return all referral records sharing the given referral code."""
        filters = [Referral.referral_code == referral_code]
        if not include_fraud:
            filters.append(Referral.is_fraud_flagged == False)  # noqa: E712
        return await self.find_many(*filters, order_by=Referral.created_at.desc())

    async def find_latest_by_code(self, referral_code: str) -> Referral | None:
        """Return the most recent non-fraud referral for a given code."""
        return await self.find_one(
            Referral.referral_code == referral_code,
            Referral.is_fraud_flagged == False,  # noqa: E712
            Referral.referral_status.not_in([ReferralStatus.EXPIRED, ReferralStatus.INVALID]),
        )

    async def find_by_referrer(
        self,
        referrer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Referral]:
        return await self.find_many(
            Referral.referrer_id == referrer_id,
            order_by=Referral.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_referred_user(self, referred_user_id: uuid.UUID) -> Referral | None:
        """Return the referral record where this user is the referred party."""
        return await self.find_one(Referral.referred_user_id == referred_user_id)

    async def find_pair(
        self,
        referrer_id: uuid.UUID,
        referred_user_id: uuid.UUID,
    ) -> Referral | None:
        """Find the unique referral for a specific referrer↔referred pair."""
        return await self.find_one(
            Referral.referrer_id == referrer_id,
            Referral.referred_user_id == referred_user_id,
        )

    # ── Status Filters ────────────────────────────────────────────────────────

    async def find_pending(self, *, skip: int = 0, limit: int = 100) -> list[Referral]:
        return await self.find_many(
            Referral.referral_status == ReferralStatus.PENDING,
            Referral.is_fraud_flagged == False,  # noqa: E712
            order_by=Referral.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_signed_up(self, *, skip: int = 0, limit: int = 100) -> list[Referral]:
        return await self.find_many(
            Referral.referral_status == ReferralStatus.SIGNED_UP,
            order_by=Referral.signed_up_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_convertible(self) -> list[Referral]:
        """SIGNED_UP referrals where the referred user has not yet completed a booking."""
        return await self.find_many(
            Referral.referral_status == ReferralStatus.SIGNED_UP,
            Referral.first_booking_id.is_(None),
            Referral.is_fraud_flagged == False,  # noqa: E712
        )

    async def find_converted(self, *, skip: int = 0, limit: int = 100) -> list[Referral]:
        return await self.find_many(
            Referral.referral_status == ReferralStatus.CONVERTED,
            order_by=Referral.converted_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_rewarded(self, *, skip: int = 0, limit: int = 100) -> list[Referral]:
        return await self.find_many(
            Referral.referral_status == ReferralStatus.REWARDED,
            order_by=Referral.rewarded_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_expired(self, *, skip: int = 0, limit: int = 100) -> list[Referral]:
        return await self.find_many(
            Referral.referral_status == ReferralStatus.EXPIRED,
            order_by=Referral.expires_at.asc(),
            skip=skip,
            limit=limit,
        )

    # ── Expiry Management ─────────────────────────────────────────────────────

    async def find_expiring_before(self, cutoff: datetime) -> list[Referral]:
        """Pending referrals whose link expires before the cutoff timestamp."""
        return await self.find_many(
            Referral.referral_status == ReferralStatus.PENDING,
            Referral.expires_at.is_not(None),
            Referral.expires_at <= cutoff,
        )

    # ── Fraud ─────────────────────────────────────────────────────────────────

    async def find_fraud_flagged(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Referral]:
        return await self.find_many(
            Referral.is_fraud_flagged == True,  # noqa: E712
            order_by=Referral.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_unreviewed_fraud(self) -> list[Referral]:
        return await self.find_many(
            Referral.is_fraud_flagged == True,  # noqa: E712
            Referral.fraud_reviewed_at.is_(None),
            order_by=Referral.created_at.asc(),
        )

    async def find_by_ip(self, ip_address: str) -> list[Referral]:
        """Fraud check: find all referrals from a given IP address."""
        return await self.find_many(
            Referral.ip_address == ip_address,
            order_by=Referral.created_at.desc(),
        )

    # ── Channel ───────────────────────────────────────────────────────────────

    async def find_by_channel(
        self,
        channel: ReferralChannel,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Referral]:
        return await self.find_many(
            Referral.channel == channel,
            order_by=Referral.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def count_by_referrer(self, referrer_id: uuid.UUID) -> dict[str, int]:
        """Return counts per status for a referrer."""
        stmt = (
            select(Referral.referral_status, func.count().label("count"))
            .where(Referral.referrer_id == referrer_id)
            .group_by(Referral.referral_status)
        )
        result = await self._session.execute(stmt)
        return {str(row.referral_status): row.count for row in result.all()}

    async def find_with_rewards(self, referral_id: uuid.UUID) -> Referral | None:
        return await self.get_by_id(
            referral_id,
            options=[selectinload(Referral.rewards)],
        )


class ReferralRewardRepository(BaseRepository[ReferralReward]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReferralReward)

    # ── Lookup ────────────────────────────────────────────────────────────────

    async def find_by_referral(self, referral_id: uuid.UUID) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.referral_id == referral_id,
            order_by=ReferralReward.created_at.asc(),
        )

    async def find_by_recipient(
        self,
        recipient_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.recipient_id == recipient_id,
            order_by=ReferralReward.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Status Filters ────────────────────────────────────────────────────────

    async def find_pending(self) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_status == ReferralRewardStatus.PENDING,
            order_by=ReferralReward.created_at.asc(),
        )

    async def find_approved(self) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_status == ReferralRewardStatus.APPROVED,
            order_by=ReferralReward.approved_at.asc(),
        )

    async def find_processing(self) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_status == ReferralRewardStatus.PROCESSING,
            order_by=ReferralReward.created_at.asc(),
        )

    async def find_failed(self) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_status == ReferralRewardStatus.FAILED,
            order_by=ReferralReward.created_at.asc(),
        )

    async def find_paid_for_recipient(
        self,
        recipient_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.recipient_id == recipient_id,
            ReferralReward.reward_status == ReferralRewardStatus.PAID,
            order_by=ReferralReward.paid_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Trigger Filters ───────────────────────────────────────────────────────

    async def find_by_trigger(
        self,
        trigger: ReferralRewardTrigger,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_trigger == trigger,
            order_by=ReferralReward.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Expiry ────────────────────────────────────────────────────────────────

    async def find_expiring_soon(self, before: datetime) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.reward_status.in_([
                ReferralRewardStatus.PENDING,
                ReferralRewardStatus.APPROVED,
            ]),
            ReferralReward.expires_at.is_not(None),
            ReferralReward.expires_at <= before,
            order_by=ReferralReward.expires_at.asc(),
        )

    async def find_expired_unclaimed(self) -> list[ReferralReward]:
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            ReferralReward.reward_status.not_in([
                ReferralRewardStatus.PAID,
                ReferralRewardStatus.EXPIRED,
                ReferralRewardStatus.CANCELLED,
            ]),
            ReferralReward.expires_at.is_not(None),
            ReferralReward.expires_at < now,
        )

    # ── Wallet Linkage ────────────────────────────────────────────────────────

    async def find_by_wallet(self, wallet_id: uuid.UUID) -> list[ReferralReward]:
        return await self.find_many(
            ReferralReward.wallet_id == wallet_id,
            order_by=ReferralReward.created_at.desc(),
        )

    async def find_with_referral(self, reward_id: uuid.UUID) -> ReferralReward | None:
        return await self.get_by_id(
            reward_id,
            options=[selectinload(ReferralReward.referral)],
        )


class ReferralMilestoneRuleRepository(BaseRepository[ReferralMilestoneRule]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReferralMilestoneRule)

    async def find_active(self) -> ReferralMilestoneRule | None:
        return await self.find_one(ReferralMilestoneRule.is_active == True)  # noqa: E712

    async def find_all_ordered(self) -> list[ReferralMilestoneRule]:
        return await self.find_many(order_by=ReferralMilestoneRule.created_at.desc())

    async def deactivate_all(self) -> None:
        from sqlalchemy import update
        await self._session.execute(
            update(ReferralMilestoneRule).values(is_active=False)
        )


class ReferralMilestoneGrantRepository(BaseRepository[ReferralMilestoneGrant]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReferralMilestoneGrant)

    async def find_by_user(self, user_id: uuid.UUID) -> list[ReferralMilestoneGrant]:
        return await self.find_many(
            ReferralMilestoneGrant.user_id == user_id,
            order_by=ReferralMilestoneGrant.created_at.desc(),
        )

    async def find_usable_for_user(self, user_id: uuid.UUID) -> list[ReferralMilestoneGrant]:
        """Grants with plans_remaining > 0, oldest first (use-it-or-lose-it order)."""
        return await self.find_many(
            ReferralMilestoneGrant.user_id == user_id,
            ReferralMilestoneGrant.plans_remaining > 0,
            order_by=ReferralMilestoneGrant.created_at.asc(),
        )

    async def find_by_grant_point(self, user_id: uuid.UUID, referral_count: int) -> ReferralMilestoneGrant | None:
        """Idempotency guard — has this exact milestone already been granted?"""
        return await self.find_one(
            ReferralMilestoneGrant.user_id == user_id,
            ReferralMilestoneGrant.referral_count_at_grant == referral_count,
        )


# ── Aggregate ─────────────────────────────────────────────────────────────────


class ReferralRepositoryAggregate:
    """Groups all referral-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.referrals = ReferralRepository(session)
        self.rewards = ReferralRewardRepository(session)
        self.milestone_rules = ReferralMilestoneRuleRepository(session)
        self.milestone_grants = ReferralMilestoneGrantRepository(session)
