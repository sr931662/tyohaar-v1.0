from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import MembershipBillingCycle, MembershipStatus
from app.models.memberships.user_membership import UserMembership as _UserMembershipModel
from app.schemas.base import CursorPage
from app.schemas.memberships.create import MembershipPlanCreate, UserMembershipCreate
from app.schemas.memberships.filters import UserMembershipFilters
from app.schemas.memberships.response import MembershipPlanResponse, UserMembershipResponse
from app.schemas.memberships.update import MembershipPlanUpdate
from app.services.base import BaseService
from app.services.memberships.exceptions import (
    MembershipAlreadyCancelledError,
    MembershipExpiredError,
    MembershipNotFoundError,
    MembershipPlanNotFoundError,
    PaymentRequiredForPaidPlanError,
    PlanDeactivationBlockedError,
)
from app.services.memberships.helpers import calculate_expiry_date
from app.services.memberships.validators import (
    validate_membership_owned_by_user,
    validate_no_active_membership,
    validate_plan_exists,
)

logger = logging.getLogger(__name__)

_BILLING_CYCLE_DAYS = {
    MembershipBillingCycle.MONTHLY: 30,
    MembershipBillingCycle.ANNUAL: 365,
}


class MembershipService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    # ── Plans ─────────────────────────────────────────────────────────────────

    async def list_plans(
        self,
        include_inactive: bool = False,
    ) -> list[MembershipPlanResponse]:
        async with self._uow() as uow:
            if include_inactive:
                plans = await uow.memberships.plans.get_all(
                    order_by=None,
                )
            else:
                plans = await uow.memberships.plans.find_active()
            return [MembershipPlanResponse.model_validate(p) for p in plans]

    async def get_plan(self, plan_id: UUID) -> MembershipPlanResponse:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.get_by_id(plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(plan_id))
            return MembershipPlanResponse.model_validate(plan)

    async def create_plan(
        self,
        data: MembershipPlanCreate,
        admin_id: UUID,
    ) -> MembershipPlanResponse:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.create_from_dict(
                data.model_dump(exclude_unset=False)
            )
            await uow.commit()
            return MembershipPlanResponse.model_validate(plan)

    async def update_plan(
        self,
        plan_id: UUID,
        data: MembershipPlanUpdate,
        admin_id: UUID,
    ) -> MembershipPlanResponse:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.get_by_id(plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(plan_id))
            updated = await uow.memberships.plans.update(
                plan, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return MembershipPlanResponse.model_validate(updated)

    async def deactivate_plan(self, plan_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.get_by_id(plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(plan_id))
            active_subs = await uow.memberships.memberships.find_many(
                _UserMembershipModel.plan_id == plan_id,
                _UserMembershipModel.membership_status == MembershipStatus.ACTIVE,
            )
            if active_subs:
                raise PlanDeactivationBlockedError()
            await uow.memberships.plans.update(plan, {"is_active": False})
            await uow.commit()

    # ── User Memberships ──────────────────────────────────────────────────────

    async def subscribe(
        self,
        user_id: UUID,
        plan_id: UUID,
        billing_cycle: MembershipBillingCycle = MembershipBillingCycle.MONTHLY,
        payment_id: UUID | None = None,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            plan = await validate_plan_exists(plan_id, uow)
            if not plan.is_active:
                raise MembershipPlanNotFoundError(str(plan_id))
            await validate_no_active_membership(user_id, uow)

            # Paid plan requires payment_id
            plan_price = plan.monthly_price if billing_cycle == MembershipBillingCycle.MONTHLY else plan.yearly_price
            from decimal import Decimal
            if plan_price > Decimal("0.00") and payment_id is None:
                raise PaymentRequiredForPaidPlanError()

            now = datetime.now(tz=timezone.utc)
            duration_days = (
                plan.validity_days
                if plan.validity_days
                else _BILLING_CYCLE_DAYS.get(billing_cycle, 30)
            )
            expires_at = now.replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            from datetime import timedelta
            expires_at = expires_at + timedelta(days=duration_days)

            membership = await uow.memberships.memberships.create_from_dict({
                "user_id": user_id,
                "plan_id": plan_id,
                "billing_cycle": billing_cycle,
                "membership_status": MembershipStatus.ACTIVE,
                "activated_at": now,
                "expires_at": expires_at,
                "payment_id": payment_id,
                "auto_renew": True,
                "renewal_count": 0,
            })
            await uow.commit()
            return UserMembershipResponse.model_validate(membership)

    async def get_active_membership(self, user_id: UUID) -> UserMembershipResponse | None:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_active_for_user(user_id)
            if membership is None:
                return None
            return UserMembershipResponse.model_validate(membership)

    async def get_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            return UserMembershipResponse.model_validate(membership)

    async def list_user_memberships(
        self,
        user_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[UserMembershipResponse]:
        async with self._uow() as uow:
            page = await uow.memberships.memberships.cursor_paginate(
                _UserMembershipModel.user_id == user_id,
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[UserMembershipResponse.model_validate(m) for m in page.items],
                next_cursor=page.next_cursor,
                page_size=page.page_size,
            )

    async def cancel_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            if membership.membership_status == MembershipStatus.CANCELLED:
                raise MembershipAlreadyCancelledError()
            if membership.membership_status != MembershipStatus.ACTIVE:
                from app.services.exceptions import BusinessRuleError
                raise BusinessRuleError("Only an active membership can be cancelled.")

            now = datetime.now(tz=timezone.utc)
            updated = await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.CANCELLED,
                "cancelled_at": now,
                "cancelled_by_id": user_id,
                "cancellation_notes": reason,
            })
            await uow.commit()
            return UserMembershipResponse.model_validate(updated)

    async def renew_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        payment_id: UUID | None = None,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)

            plan = await uow.memberships.plans.get_by_id(membership.plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(membership.plan_id))

            plan_price = (
                plan.monthly_price
                if membership.billing_cycle == MembershipBillingCycle.MONTHLY
                else plan.yearly_price
            )
            from decimal import Decimal
            if plan_price > Decimal("0.00") and payment_id is None:
                raise PaymentRequiredForPaidPlanError()

            duration_days = (
                plan.validity_days
                if plan.validity_days
                else _BILLING_CYCLE_DAYS.get(membership.billing_cycle, 30)
            )

            from datetime import timedelta
            current_expires = membership.expires_at or datetime.now(tz=timezone.utc)
            new_expires = current_expires + timedelta(days=duration_days)

            now = datetime.now(tz=timezone.utc)
            history = list(membership.renewal_history or [])
            history.append({
                "renewed_at": now.isoformat(),
                "payment_id": str(payment_id) if payment_id else None,
                "from_expires_at": current_expires.isoformat() if current_expires else None,
                "to_expires_at": new_expires.isoformat(),
                "billing_cycle": membership.billing_cycle.value
                if hasattr(membership.billing_cycle, "value")
                else str(membership.billing_cycle),
            })

            updated = await uow.memberships.memberships.update(membership, {
                "expires_at": new_expires,
                "renewal_count": membership.renewal_count + 1,
                "renewal_history": history,
                "membership_status": MembershipStatus.ACTIVE,
            })
            await uow.commit()
            return UserMembershipResponse.model_validate(updated)

    async def check_membership_feature_access(
        self,
        user_id: UUID,
        feature_key: str,
    ) -> bool:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_active_for_user(user_id)
            if membership is None:
                return False
            plan = await uow.memberships.plans.get_by_id(membership.plan_id)
            if plan is None:
                return False

            feature_map: dict[str, bool] = {
                "priority_booking": plan.priority_booking,
                "exclusive_packages": plan.has_exclusive_packages,
                "cancellation_protection": plan.cancellation_protection,
                "cashback": plan.cashback_percentage > 0,
                "wallet_bonus": plan.wallet_bonus > 0,
                "free_invitations": plan.free_invitations_count > 0,
            }
            if feature_key in feature_map:
                return feature_map[feature_key]

            if plan.benefits and isinstance(plan.benefits, dict):
                val = plan.benefits.get(feature_key)
                if isinstance(val, bool):
                    return val
                return val is not None

            return False

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def list_all_memberships(
        self,
        filters: object,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[UserMembershipResponse]:
        async with self._uow() as uow:
            page = await uow.memberships.memberships.cursor_paginate(
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[UserMembershipResponse.model_validate(m) for m in page.items],
                next_cursor=page.next_cursor,
                page_size=page.page_size,
            )

    async def force_expire_membership(
        self,
        membership_id: UUID,
        admin_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_by_id(membership_id)
            if membership is None:
                raise MembershipNotFoundError(str(membership_id))
            now = datetime.now(tz=timezone.utc)
            await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.EXPIRED,
                "expires_at": now,
            })
            await uow.commit()
