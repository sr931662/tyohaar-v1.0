from __future__ import annotations

from uuid import UUID

from app.models.enums import MembershipStatus
from app.models.memberships.membership_plan import MembershipPlan
from app.models.memberships.user_membership import UserMembership
from app.repositories.unit_of_work import UnitOfWork
from app.services.memberships.exceptions import (
    ActiveMembershipExistsError,
    MembershipNotFoundError,
    MembershipOwnershipError,
    MembershipPlanNotFoundError,
)


async def validate_plan_exists(plan_id: UUID, uow: UnitOfWork) -> MembershipPlan:
    plan = await uow.memberships.plans.get_by_id(plan_id)
    if plan is None:
        raise MembershipPlanNotFoundError(str(plan_id))
    return plan


async def validate_no_active_membership(user_id: UUID, uow: UnitOfWork) -> None:
    existing = await uow.memberships.memberships.get_active_for_user(user_id)
    if existing is not None:
        raise ActiveMembershipExistsError()


async def validate_membership_owned_by_user(
    membership_id: UUID,
    user_id: UUID,
    uow: UnitOfWork,
) -> UserMembership:
    membership = await uow.memberships.memberships.get_by_id(membership_id)
    if membership is None:
        raise MembershipNotFoundError(str(membership_id))
    if membership.user_id != user_id:
        raise MembershipOwnershipError()
    return membership
