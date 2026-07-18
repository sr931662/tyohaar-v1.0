"""
DiscountEngine — the single centralized service for discount eligibility,
priority/stacking resolution, calculation, and usage tracking.

Reusable from bookings (create_booking), payments (post-payment redemption
recording), admin preview, and any future checkout surface — no discount
logic should live anywhere else. See Coupon (server/app/models/payments/
coupon.py) for the full field reference.

Stacking resolution: every eligible discount is either stackable or not
(Coupon.is_stackable). If any non-stackable discounts are eligible, exactly
one is chosen (lowest Coupon.priority, tie-broken by highest computed
discount amount) and combined with *all* eligible stackable discounts. This
single rule produces every stacking behaviour a coupon config might want:
mutually-exclusive-only, priority-based, "highest discount wins", or full
stacking — purely from the two per-discount fields, no separate mode enum.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import CouponAdminStatus, CouponType
from app.models.payments.coupon import Coupon
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.payments.response import AppliedDiscountItem, DiscountEvaluationResponse
from app.services.base import BaseService
from app.services.common.rule_conditions import evaluate_conditions
from app.services.payments.helpers import calculate_discount_amount

logger = logging.getLogger(__name__)


class DiscountEngine(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Public entrypoint ────────────────────────────────────────────────────

    async def evaluate(
        self,
        uow: UnitOfWork,
        *,
        customer_id: UUID,
        subtotal: Decimal,
        package_id: UUID | None = None,
        occasion_id: UUID | None = None,
        coupon_code: str | None = None,
    ) -> DiscountEvaluationResponse:
        """
        Evaluate every applicable discount for this basket and return the
        resolved, itemized result. Reuses the SAME uow/transaction as the
        caller (booking creation) so evaluation reads are consistent with
        whatever the caller is about to write — never opens its own uow here.
        """
        now = datetime.now(tz=timezone.utc)

        package = await uow.packages.packages.get_by_id(package_id) if package_id else None
        vendor_id = package.vendor_id if package is not None else None
        occasion = await uow.occasions.occasions.get_by_id(occasion_id) if occasion_id else None

        membership_tier = await self._resolve_membership_tier(uow, customer_id)
        is_first_booking = await self._is_first_booking(uow, customer_id)
        is_referred_user = await self._is_referred_user(uow, customer_id)

        model = uow.payments.coupons._model
        automatic_candidates = await uow.payments.coupons.find_many(
            model.is_automatic == True,  # noqa: E712
            model.is_active == True,  # noqa: E712
            model.admin_status == CouponAdminStatus.PUBLISHED,
            model.valid_from <= now,
            (model.valid_until.is_(None)) | (model.valid_until >= now),
        )

        candidates: list[Coupon] = list(automatic_candidates)
        explicit_coupon: Coupon | None = None
        coupon_error: str | None = None

        if coupon_code:
            explicit_coupon = await uow.payments.coupons.find_by_code(coupon_code)
            if explicit_coupon is None:
                coupon_error = "Coupon code not found."
            elif explicit_coupon.id not in {c.id for c in candidates}:
                candidates.append(explicit_coupon)

        eligible: list[tuple[Coupon, Decimal]] = []
        for coupon in candidates:
            ok, reason = await self._check_eligibility(
                uow,
                coupon,
                now=now,
                customer_id=customer_id,
                subtotal=subtotal,
                package=package,
                vendor_id=vendor_id,
                occasion=occasion,
                membership_tier=membership_tier,
                is_first_booking=is_first_booking,
                is_referred_user=is_referred_user,
            )
            is_the_explicit_one = explicit_coupon is not None and coupon.id == explicit_coupon.id
            if not ok:
                if is_the_explicit_one:
                    coupon_error = reason
                continue

            try:
                amount = calculate_discount_amount(
                    subtotal,
                    coupon.coupon_type,
                    coupon.discount_value,
                    coupon.max_discount_amount,
                    package_base_price=package.base_price if package is not None else None,
                )
            except ValueError as exc:
                if is_the_explicit_one:
                    coupon_error = str(exc)
                continue

            if amount <= Decimal("0.00"):
                if is_the_explicit_one:
                    coupon_error = "This coupon does not produce a discount for the current basket."
                continue

            eligible.append((coupon, amount))

        applied = self._resolve_stacking(eligible)

        total_discount = min(sum((amt for _, amt in applied), Decimal("0.00")), subtotal)
        final_amount = subtotal - total_discount

        return DiscountEvaluationResponse(
            original_amount=subtotal,
            applied_discounts=[
                AppliedDiscountItem(
                    coupon_id=c.id,
                    title=c.title,
                    public_offer_title=c.public_offer_title,
                    code=c.code,
                    coupon_type=c.coupon_type,
                    discount_amount=amt,
                )
                for c, amt in applied
            ],
            total_discount=total_discount,
            final_amount=final_amount,
            coupon_error=coupon_error,
        )

    # ── Stacking resolution ──────────────────────────────────────────────────

    def _resolve_stacking(
        self, eligible: list[tuple[Coupon, Decimal]]
    ) -> list[tuple[Coupon, Decimal]]:
        if not eligible:
            return []

        stackable = [pair for pair in eligible if pair[0].is_stackable]
        exclusive = [pair for pair in eligible if not pair[0].is_stackable]

        if not exclusive:
            return stackable

        # Lowest priority number wins; tie-broken by highest discount amount.
        best_exclusive = min(exclusive, key=lambda pair: (pair[0].priority, -pair[1]))
        return [best_exclusive, *stackable]

    # ── Eligibility checks ───────────────────────────────────────────────────

    async def _check_eligibility(
        self,
        uow: UnitOfWork,
        coupon: Coupon,
        *,
        now: datetime,
        customer_id: UUID,
        subtotal: Decimal,
        package,
        vendor_id: UUID | None,
        occasion,
        membership_tier: str | None,
        is_first_booking: bool,
        is_referred_user: bool,
    ) -> tuple[bool, str | None]:
        if coupon.admin_status == CouponAdminStatus.ARCHIVED:
            return False, "This offer is no longer available."
        if coupon.admin_status == CouponAdminStatus.DRAFT:
            return False, "This offer is not yet published."
        if coupon.admin_status == CouponAdminStatus.PAUSED or not coupon.is_active:
            return False, "This offer is currently paused."
        if coupon.valid_from > now:
            return False, "This offer is not yet valid."
        if coupon.valid_until is not None and coupon.valid_until < now:
            return False, "This offer has expired."
        if coupon.is_exhausted:
            return False, "This offer's usage limit has been reached."

        if coupon.min_order_value is not None and subtotal < coupon.min_order_value:
            return False, f"Minimum order amount of ₹{coupon.min_order_value} is required."
        if coupon.min_package_value is not None:
            base = package.base_price if package is not None else Decimal("0.00")
            if base < coupon.min_package_value:
                return False, f"Minimum package value of ₹{coupon.min_package_value} is required."

        if coupon.first_booking_only and not is_first_booking:
            return False, "This offer is only available on your first booking."
        if coupon.repeat_customers_only and is_first_booking:
            return False, "This offer is only available to returning customers."
        if coupon.referral_users_only and not is_referred_user:
            return False, "This offer is only available to customers who joined via referral."

        if coupon.eligible_membership_tiers:
            if membership_tier is None or membership_tier not in coupon.eligible_membership_tiers:
                return False, "This offer requires an eligible membership tier."

        if coupon.applicable_vendor_ids:
            if vendor_id is None or str(vendor_id) not in coupon.applicable_vendor_ids:
                return False, "This offer is not applicable to the selected vendor."

        if coupon.applicable_package_ids:
            if package is None or str(package.id) not in coupon.applicable_package_ids:
                return False, "This offer is not applicable to the selected package."

        if coupon.applicable_occasion_ids:
            if occasion is None or str(occasion.id) not in coupon.applicable_occasion_ids:
                return False, "This offer is not applicable to the selected occasion."

        if coupon.applicable_occasion_categories:
            category_slug = None
            if occasion is not None and occasion.category_id is not None:
                category = await uow.occasions.categories.get_by_id(occasion.category_id)
                category_slug = category.slug if category is not None else None
            if category_slug is None or category_slug not in coupon.applicable_occasion_categories:
                return False, "This offer is not applicable to the selected occasion category."

        if coupon.per_user_limit is not None:
            used = await uow.payments.coupon_redemptions.count_for_user(coupon.id, customer_id)
            if used >= coupon.per_user_limit:
                label = coupon.code or coupon.title
                return False, (
                    f"You have already used '{label}' the maximum "
                    f"{coupon.per_user_limit} time(s) allowed."
                )

        if coupon.max_uses_per_day is not None:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            used_today = await uow.payments.coupon_redemptions.count_for_coupon_since(
                coupon.id, day_start
            )
            if used_today >= coupon.max_uses_per_day:
                return False, "This offer's daily usage limit has been reached."

        if coupon.condition_rules:
            payload = {
                "day_of_week": now.weekday(),  # 0=Monday .. 6=Sunday
                "hour_of_day": now.hour,
                "is_first_booking": is_first_booking,
                "is_referred_user": is_referred_user,
                "membership_tier": membership_tier,
                "subtotal": float(subtotal),
            }
            if not evaluate_conditions(coupon.condition_rules, payload):
                return False, "This offer's conditions are not currently met."

        return True, None

    async def _resolve_membership_tier(self, uow: UnitOfWork, customer_id: UUID) -> str | None:
        membership = await uow.memberships.memberships.get_active_or_grace_for_user(customer_id)
        if membership is None:
            return None
        plan = await uow.memberships.plans.get_by_id(membership.plan_id)
        return plan.tier if plan is not None else None

    async def _is_first_booking(self, uow: UnitOfWork, customer_id: UUID) -> bool:
        existing = await uow.bookings.bookings.find_many(
            uow.bookings.bookings._model.customer_id == customer_id,
            limit=1,
        )
        return not existing

    async def _is_referred_user(self, uow: UnitOfWork, customer_id: UUID) -> bool:
        referral = await uow.referrals.referrals.find_by_referred_user(customer_id)
        return referral is not None

    # ── Usage recording ──────────────────────────────────────────────────────

    async def record_usage(
        self,
        *,
        coupon_ids: list[UUID],
        user_id: UUID,
        payment_id: UUID,
    ) -> None:
        """
        Record redemption for each applied discount, idempotently. Called
        best-effort after a payment is confirmed COMPLETED — same invocation
        convention as ReferralService.trigger_referral_rewards (own uow,
        try/except at the call site, never breaks a successful payment).
        """
        if not coupon_ids:
            return
        async with self._uow() as uow:
            for coupon_id in coupon_ids:
                already = await uow.payments.coupon_redemptions.exists_for_payment(
                    coupon_id, payment_id
                )
                if already:
                    continue

                coupon = await uow.payments.coupons.get_with_lock(coupon_id)
                if coupon is None:
                    continue

                await uow.payments.coupon_redemptions.create_from_dict({
                    "coupon_id": coupon_id,
                    "user_id": user_id,
                    "payment_id": payment_id,
                })
                await uow.payments.coupons.increment_usage(coupon_id)
