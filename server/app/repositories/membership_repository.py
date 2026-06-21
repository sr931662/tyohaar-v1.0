"""
Membership repository — UserMembership and MembershipPlan.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import MembershipStatus
from app.models.memberships.membership_plan import MembershipPlan
from app.models.memberships.user_membership import UserMembership
from app.repositories.base import BaseRepository


class MembershipPlanRepository(BaseRepository[MembershipPlan]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MembershipPlan)

    async def find_active(self) -> list[MembershipPlan]:
        return await self.find_many(
            MembershipPlan.is_active == True,  # noqa: E712
            order_by=MembershipPlan.display_order.asc(),
        )

    async def find_by_slug(self, slug: str) -> MembershipPlan | None:
        return await self.find_one(MembershipPlan.slug == slug)

    async def find_by_tier(self, tier: str) -> MembershipPlan | None:
        return await self.find_one(MembershipPlan.tier == tier)


class UserMembershipRepository(BaseRepository[UserMembership]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserMembership)

    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserMembership]:
        return await self.find_many(
            UserMembership.user_id == user_id,
            order_by=UserMembership.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def get_active_for_user(self, user_id: uuid.UUID) -> UserMembership | None:
        """Return the single ACTIVE membership for a user (enforced by partial unique index)."""
        return await self.find_one(
            UserMembership.user_id == user_id,
            UserMembership.membership_status == MembershipStatus.ACTIVE,
        )

    async def find_by_plan(
        self,
        plan_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserMembership]:
        return await self.find_many(
            UserMembership.plan_id == plan_id,
            skip=skip,
            limit=limit,
        )

    async def find_expiring_before(self, cutoff: datetime) -> list[UserMembership]:
        """Return ACTIVE memberships expiring before the cutoff timestamp."""
        return await self.find_many(
            UserMembership.membership_status == MembershipStatus.ACTIVE,
            UserMembership.expires_at <= cutoff,
            order_by=UserMembership.expires_at.asc(),
        )

    async def find_in_grace_period(self) -> list[UserMembership]:
        return await self.find_many(
            UserMembership.membership_status == MembershipStatus.GRACE_PERIOD,
        )

    async def find_expired(self, *, skip: int = 0, limit: int = 100) -> list[UserMembership]:
        return await self.find_many(
            UserMembership.membership_status == MembershipStatus.EXPIRED,
            skip=skip,
            limit=limit,
        )

    async def find_by_status(
        self,
        status: MembershipStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserMembership]:
        return await self.find_many(
            UserMembership.membership_status == status,
            skip=skip,
            limit=limit,
        )

    async def get_with_plan(self, membership_id: uuid.UUID) -> UserMembership | None:
        return await self.get_by_id(
            membership_id,
            options=[selectinload(UserMembership.plan)],
        )

    async def count_active_by_plan(self) -> dict[str, int]:
        from sqlalchemy import func
        stmt = (
            select(UserMembership.plan_id, func.count().label("count"))
            .where(UserMembership.membership_status == MembershipStatus.ACTIVE)
            .group_by(UserMembership.plan_id)
        )
        result = await self._session.execute(stmt)
        return {str(row.plan_id): row.count for row in result.all()}


class MembershipRepositoryAggregate:
    """Groups membership-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.plans = MembershipPlanRepository(session)
        self.memberships = UserMembershipRepository(session)
