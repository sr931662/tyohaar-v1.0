"""
MembershipService — plans, subscriptions, lifecycle (grace period), upgrades/downgrades.

Lifecycle state machine (no cron in this codebase — resolved lazily on every
read/mutate path via _resolve_lifecycle_state):

    ACTIVE --[expires_at reached]--> GRACE_PERIOD --[renewed]--> ACTIVE
                                            |
                                            +--[grace_period_until reached]--> EXPIRED

Side effects that must not roll back with the owning transaction (wallet
bonus credits) are executed AFTER the `async with self._uow()` block exits,
matching the convention used elsewhere in this codebase.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import MembershipBillingCycle, MembershipStatus
from app.models.memberships.membership_plan import MembershipPlan
from app.models.memberships.user_membership import MembershipCancellationReason
from app.models.memberships.user_membership import UserMembership as _UserMembershipModel
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.base import CursorPage
from app.schemas.memberships.create import MembershipPlanCreate, UserMembershipCreate
from app.schemas.memberships.filters import UserMembershipFilters
from app.schemas.memberships.response import MembershipPlanResponse, UserMembershipResponse
from app.schemas.memberships.update import MembershipPlanUpdate
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError
from app.services.memberships.exceptions import (
    MembershipAlreadyCancelledError,
    MembershipDowngradeNotAllowedError,
    MembershipNotEligibleForChangeError,
    MembershipNotFoundError,
    MembershipPlanNotFoundError,
    MembershipUpgradeNotAllowedError,
    PaymentRequiredForPaidPlanError,
    PlanDeactivationBlockedError,
)
from app.services.memberships.validators import (
    validate_membership_owned_by_user,
    validate_no_active_membership,
    validate_plan_exists,
)

logger = logging.getLogger(__name__)

_BILLING_CYCLE_DAYS = {
    MembershipBillingCycle.MONTHLY: 30,
    MembershipBillingCycle.QUARTERLY: 90,
    MembershipBillingCycle.ANNUAL: 365,
}

GRACE_PERIOD_DAYS = 7


def _price_for_cycle(plan: MembershipPlan, billing_cycle: MembershipBillingCycle) -> Decimal:
    if billing_cycle == MembershipBillingCycle.MONTHLY:
        return plan.monthly_price
    if billing_cycle == MembershipBillingCycle.ANNUAL:
        return plan.yearly_price
    # QUARTERLY has no dedicated price column on MembershipPlan — approximate as 3x monthly.
    return plan.monthly_price * 3


class MembershipService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    # ── Response building ────────────────────────────────────────────────────

    async def _to_membership_response(
        self,
        uow: UnitOfWork,
        membership: _UserMembershipModel,
        plan: MembershipPlan | None = None,
    ) -> UserMembershipResponse:
        """
        Build a UserMembershipResponse explicitly rather than via
        model_validate(membership) — `tier` lives on MembershipPlan, not
        UserMembership, and the `plan` relationship is lazy="noload" (unsafe
        to touch under the async engine without an explicit eager-load).
        """
        if plan is None:
            plan = await uow.memberships.plans.get_by_id(membership.plan_id)
        return UserMembershipResponse(
            id=membership.id,
            user_id=membership.user_id,
            plan_id=membership.plan_id,
            tier=plan.tier if plan else None,
            billing_cycle=membership.billing_cycle,
            membership_status=membership.membership_status,
            is_lifetime=membership.is_lifetime,
            activated_at=membership.activated_at,
            expires_at=membership.expires_at,
            next_renewal_at=membership.next_renewal_at,
            grace_period_until=membership.grace_period_until,
            auto_renew=membership.auto_renew,
            renewal_count=membership.renewal_count,
            payment_id=membership.payment_id,
            upgraded_from_plan_id=membership.upgraded_from_plan_id,
            upgrade_reason=membership.upgrade_reason,
            cancellation_reason=(
                membership.cancellation_reason.value if membership.cancellation_reason else None
            ),
            cancellation_notes=membership.cancellation_notes,
            cancelled_at=membership.cancelled_at,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )

    # ── Lifecycle state machine ──────────────────────────────────────────────

    async def _resolve_lifecycle_state(
        self,
        uow: UnitOfWork,
        membership: _UserMembershipModel,
    ) -> _UserMembershipModel:
        """
        Idempotently advance membership_status per the grace-period state
        machine, given the current time. Persists the transition if one
        occurred and returns the (possibly updated) membership.
        """
        if membership.is_lifetime or membership.expires_at is None:
            return membership

        now = datetime.now(tz=timezone.utc)

        if membership.membership_status == MembershipStatus.ACTIVE and now >= membership.expires_at:
            return await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.GRACE_PERIOD,
                "grace_period_until": membership.expires_at + timedelta(days=GRACE_PERIOD_DAYS),
            })

        if (
            membership.membership_status == MembershipStatus.GRACE_PERIOD
            and membership.grace_period_until is not None
            and now >= membership.grace_period_until
        ):
            return await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.EXPIRED,
            })

        return membership

    async def sweep_expired_memberships(self) -> int:
        """
        Batch-apply the lifecycle state machine to every ACTIVE/GRACE_PERIOD
        membership whose window has passed. No cron exists in this codebase
        yet — this is reachable via an admin-only route for manual triggering
        or an external scheduled hit; wiring a real scheduler is a follow-up.
        """
        async with self._uow() as uow:
            now = datetime.now(tz=timezone.utc)
            expiring = await uow.memberships.memberships.find_expiring_before(now)
            in_grace = await uow.memberships.memberships.find_in_grace_period()
            transitioned = 0
            for membership in [*expiring, *in_grace]:
                before = membership.membership_status
                membership = await self._resolve_lifecycle_state(uow, membership)
                if membership.membership_status != before:
                    transitioned += 1
            await uow.commit()
            return transitioned

    # ── Wallet bonus (post-commit side effect) ───────────────────────────────

    async def _credit_wallet_bonus(self, user_id: UUID, plan: MembershipPlan, occasion: str) -> None:
        from app.services.wallets.service import WalletService

        try:
            await WalletService(self._session_factory).credit_wallet(
                user_id=user_id,
                amount=plan.wallet_bonus,
                description=f"{occasion} bonus — {plan.name}",
                reference_type="membership",
            )
        except Exception:
            logger.exception("Wallet bonus credit failed for user=%s plan=%s", user_id, plan.id)

    # ── Plans ─────────────────────────────────────────────────────────────────

    async def list_plans(
        self,
        include_inactive: bool = False,
    ) -> list[MembershipPlanResponse]:
        async with self._uow() as uow:
            if include_inactive:
                plans = await uow.memberships.plans.get_all(order_by=None)
            else:
                plans = await uow.memberships.plans.find_active()
            return [MembershipPlanResponse.model_validate(p) for p in plans]

    async def get_plan(self, plan_id: UUID) -> MembershipPlanResponse:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.get_by_id(plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(plan_id))
            return MembershipPlanResponse.model_validate(plan)

    async def create_plan(self, data: MembershipPlanCreate) -> MembershipPlanResponse:
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

    async def deactivate_plan(self, plan_id: UUID) -> MembershipPlanResponse:
        async with self._uow() as uow:
            plan = await uow.memberships.plans.get_by_id(plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(plan_id))
            active_subs = await uow.memberships.memberships.find_many(
                _UserMembershipModel.plan_id == plan_id,
                _UserMembershipModel.membership_status.in_(
                    [MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD]
                ),
            )
            if active_subs:
                raise PlanDeactivationBlockedError()
            updated = await uow.memberships.plans.update(plan, {"is_active": False})
            await uow.commit()
            return MembershipPlanResponse.model_validate(updated)

    # ── User Memberships ──────────────────────────────────────────────────────

    async def subscribe(
        self,
        user_id: UUID,
        data: UserMembershipCreate,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            plan = await validate_plan_exists(data.plan_id, uow)
            if not plan.is_active:
                raise MembershipPlanNotFoundError(str(data.plan_id))
            await validate_no_active_membership(user_id, uow)

            plan_price = _price_for_cycle(plan, data.billing_cycle)
            if plan_price > Decimal("0.00") and data.payment_id is None:
                raise PaymentRequiredForPaidPlanError()

            now = datetime.now(tz=timezone.utc)
            duration_days = plan.validity_days or _BILLING_CYCLE_DAYS.get(data.billing_cycle, 30)
            expires_at = now.replace(
                hour=23, minute=59, second=59, microsecond=0
            ) + timedelta(days=duration_days)

            membership = await uow.memberships.memberships.create_from_dict({
                "user_id": user_id,
                "plan_id": data.plan_id,
                "billing_cycle": data.billing_cycle,
                "membership_status": MembershipStatus.ACTIVE,
                "activated_at": now,
                "expires_at": expires_at,
                "payment_id": data.payment_id,
                "auto_renew": data.auto_renew,
                "renewal_count": 0,
            })
            await uow.commit()
            result = await self._to_membership_response(uow, membership, plan=plan)

        if plan.wallet_bonus > Decimal("0.00"):
            await self._credit_wallet_bonus(user_id, plan, occasion="Welcome")

        return result

    async def get_active_membership(self, user_id: UUID) -> UserMembershipResponse | None:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_active_or_grace_for_user(user_id)
            if membership is None:
                return None
            membership = await self._resolve_lifecycle_state(uow, membership)
            await uow.commit()
            if membership.membership_status not in (
                MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD
            ):
                return None
            return await self._to_membership_response(uow, membership)

    async def get_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            membership = await self._resolve_lifecycle_state(uow, membership)
            await uow.commit()
            return await self._to_membership_response(uow, membership)

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
            items = []
            for membership in page.items:
                membership = await self._resolve_lifecycle_state(uow, membership)
                items.append(await self._to_membership_response(uow, membership))
            await uow.commit()
            return CursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.next_cursor is not None,
            )

    async def cancel_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            membership = await self._resolve_lifecycle_state(uow, membership)

            if membership.membership_status == MembershipStatus.CANCELLED:
                raise MembershipAlreadyCancelledError()
            if membership.membership_status not in (
                MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD
            ):
                raise BusinessRuleError("Only an active or grace-period membership can be cancelled.")

            now = datetime.now(tz=timezone.utc)
            updated = await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.CANCELLED,
                "cancellation_reason": MembershipCancellationReason.CUSTOMER_REQUEST,
                "cancellation_notes": reason,
                "cancelled_at": now,
                "cancelled_by_id": user_id,
            })
            await uow.commit()
            return await self._to_membership_response(uow, updated)

    async def renew_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        payment_id: UUID | None = None,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            membership = await self._resolve_lifecycle_state(uow, membership)

            if membership.membership_status not in (
                MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD
            ):
                raise MembershipNotEligibleForChangeError()

            plan = await uow.memberships.plans.get_by_id(membership.plan_id)
            if plan is None:
                raise MembershipPlanNotFoundError(str(membership.plan_id))

            plan_price = _price_for_cycle(plan, membership.billing_cycle)
            if plan_price > Decimal("0.00") and payment_id is None:
                raise PaymentRequiredForPaidPlanError()

            duration_days = plan.validity_days or _BILLING_CYCLE_DAYS.get(membership.billing_cycle, 30)
            now = datetime.now(tz=timezone.utc)

            # A lapsed grace period means expires_at is stale — renewing from
            # "now" instead avoids silently absorbing the grace week into (or
            # double-counting it against) the new period. An active renewal
            # extends from the current expiry, preserving unused days.
            was_in_grace = membership.membership_status == MembershipStatus.GRACE_PERIOD
            base = now if was_in_grace else (membership.expires_at or now)
            new_expires = base + timedelta(days=duration_days)

            history = list(membership.renewal_history or [])
            history.append({
                "renewed_at": now.isoformat(),
                "payment_id": str(payment_id) if payment_id else None,
                "from_expires_at": membership.expires_at.isoformat() if membership.expires_at else None,
                "to_expires_at": new_expires.isoformat(),
                "billing_cycle": membership.billing_cycle.value,
            })

            updated = await uow.memberships.memberships.update(membership, {
                "expires_at": new_expires,
                "renewal_count": membership.renewal_count + 1,
                "renewal_history": history,
                "membership_status": MembershipStatus.ACTIVE,
                "grace_period_until": None,
                "payment_id": payment_id or membership.payment_id,
            })
            await uow.commit()
            return await self._to_membership_response(uow, updated, plan=plan)

    # ── Upgrade / Downgrade ──────────────────────────────────────────────────

    async def upgrade_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        new_plan_id: UUID,
        payment_id: UUID | None = None,
        reason: str | None = None,
    ) -> UserMembershipResponse:
        return await self._change_plan(
            membership_id, user_id, new_plan_id, payment_id, reason, is_upgrade=True
        )

    async def downgrade_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
        new_plan_id: UUID,
        reason: str | None = None,
    ) -> UserMembershipResponse:
        return await self._change_plan(
            membership_id, user_id, new_plan_id, None, reason, is_upgrade=False
        )

    async def _change_plan(
        self,
        membership_id: UUID,
        user_id: UUID,
        new_plan_id: UUID,
        payment_id: UUID | None,
        reason: str | None,
        is_upgrade: bool,
    ) -> UserMembershipResponse:
        """
        No proration: the current subscription is cancelled and a new one
        starts immediately for a fresh full period. Allowed from ACTIVE or
        GRACE_PERIOD (a customer can upgrade/downgrade during their grace
        week without losing continuity) — not from EXPIRED/CANCELLED, which
        must go through subscribe() instead.
        """
        async with self._uow() as uow:
            membership = await validate_membership_owned_by_user(membership_id, user_id, uow)
            membership = await self._resolve_lifecycle_state(uow, membership)

            if membership.membership_status not in (
                MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD
            ):
                raise MembershipNotEligibleForChangeError()

            current_plan = await uow.memberships.plans.get_by_id(membership.plan_id)
            if current_plan is None:
                raise MembershipPlanNotFoundError(str(membership.plan_id))

            new_plan = await uow.memberships.plans.get_by_id(new_plan_id)
            if new_plan is None or not new_plan.is_active:
                raise MembershipPlanNotFoundError(str(new_plan_id))

            allowed_tier = (
                current_plan.can_upgrade_to_tier if is_upgrade else current_plan.can_downgrade_to_tier
            )
            if allowed_tier is None or new_plan.tier != allowed_tier:
                if is_upgrade:
                    raise MembershipUpgradeNotAllowedError()
                raise MembershipDowngradeNotAllowedError()

            if is_upgrade:
                new_price = _price_for_cycle(new_plan, membership.billing_cycle)
                if new_price > Decimal("0.00") and payment_id is None:
                    raise PaymentRequiredForPaidPlanError()

            now = datetime.now(tz=timezone.utc)
            cancel_reason = (
                MembershipCancellationReason.UPGRADED
                if is_upgrade
                else MembershipCancellationReason.DOWNGRADED
            )
            await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.CANCELLED,
                "cancellation_reason": cancel_reason,
                "cancellation_notes": reason,
                "cancelled_at": now,
            })

            duration_days = new_plan.validity_days or _BILLING_CYCLE_DAYS.get(membership.billing_cycle, 30)
            expires_at = now.replace(
                hour=23, minute=59, second=59, microsecond=0
            ) + timedelta(days=duration_days)

            new_membership = await uow.memberships.memberships.create_from_dict({
                "user_id": user_id,
                "plan_id": new_plan_id,
                "billing_cycle": membership.billing_cycle,
                "membership_status": MembershipStatus.ACTIVE,
                "activated_at": now,
                "expires_at": expires_at,
                "payment_id": payment_id,
                "upgraded_from_plan_id": current_plan.id,
                "upgrade_reason": reason,
                "auto_renew": membership.auto_renew,
                "renewal_count": 0,
            })
            await uow.commit()
            result = await self._to_membership_response(uow, new_membership, plan=new_plan)

        if is_upgrade and new_plan.wallet_bonus > Decimal("0.00"):
            await self._credit_wallet_bonus(user_id, new_plan, occasion="Upgrade")

        return result

    # ── Feature access ────────────────────────────────────────────────────────

    async def check_feature_access(self, user_id: UUID, feature_key: str) -> bool:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_active_or_grace_for_user(user_id)
            if membership is None:
                return False
            membership = await self._resolve_lifecycle_state(uow, membership)
            if membership.membership_status not in (
                MembershipStatus.ACTIVE, MembershipStatus.GRACE_PERIOD
            ):
                await uow.commit()
                return False

            plan = await uow.memberships.plans.get_by_id(membership.plan_id)
            await uow.commit()
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
        filters: UserMembershipFilters | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage[UserMembershipResponse]:
        conditions = []
        if filters is not None:
            if filters.user_id is not None:
                conditions.append(_UserMembershipModel.user_id == filters.user_id)
            if filters.plan_id is not None:
                conditions.append(_UserMembershipModel.plan_id == filters.plan_id)
            if filters.status is not None:
                conditions.append(_UserMembershipModel.membership_status == filters.status)
            if filters.billing_cycle is not None:
                conditions.append(_UserMembershipModel.billing_cycle == filters.billing_cycle)
            if filters.auto_renew is not None:
                conditions.append(_UserMembershipModel.auto_renew == filters.auto_renew)
            if filters.from_date is not None:
                conditions.append(_UserMembershipModel.expires_at >= filters.from_date)
            if filters.to_date is not None:
                conditions.append(_UserMembershipModel.expires_at <= filters.to_date)

        async with self._uow() as uow:
            page = await uow.memberships.memberships.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            items = []
            for membership in page.items:
                membership = await self._resolve_lifecycle_state(uow, membership)
                items.append(await self._to_membership_response(uow, membership))
            await uow.commit()
            return CursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.next_cursor is not None,
            )

    async def force_expire_membership(
        self,
        membership_id: UUID,
        admin_id: UUID,
    ) -> UserMembershipResponse:
        async with self._uow() as uow:
            membership = await uow.memberships.memberships.get_by_id(membership_id)
            if membership is None:
                raise MembershipNotFoundError(str(membership_id))
            now = datetime.now(tz=timezone.utc)
            updated = await uow.memberships.memberships.update(membership, {
                "membership_status": MembershipStatus.EXPIRED,
                "expires_at": now,
                "grace_period_until": None,
            })
            await uow.commit()
            return await self._to_membership_response(uow, updated)
