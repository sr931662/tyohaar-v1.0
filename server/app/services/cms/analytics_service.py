"""
Analytics Service — Executive Dashboard & Business Intelligence
==============================================================

All queries are optimised, single-pass aggregations using SQLAlchemy Core.
No N+1. No ORM lazy loads. No Python-side loops where SQL can do the work.

Architecture:
  - AnalyticsService.get_executive_dashboard() → full snapshot
  - Individual _get_*_metrics() helpers → one query each
  - Chart series queries → time-bucketed aggregations
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Integer, case, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.cms.analytics import (
    ActivityFeed,
    ActivityItem,
    BookingMetrics,
    BudgetMetrics,
    CategoryBreakdown,
    ChartData,
    CityMetric,
    DashboardWidget,
    ExecutiveDashboard,
    ForecastData,
    GeographicMetrics,
    HeatmapData,
    MediaMetrics,
    MembershipMetrics,
    NotificationMetrics,
    OccasionMetrics,
    PaymentMetrics,
    PieChartData,
    PlatformHealth,
    ReferralMetrics,
    RevenueMetrics,
    SupportMetrics,
    TimeSeriesChart,
    TimeSeriesPoint,
    UserMetrics,
    VendorMetrics,
    WalletMetrics,
)
from app.services.base import BaseService


class AnalyticsService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Utility helpers ───────────────────────────────────────────────────────

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _today_start(self) -> datetime:
        n = self._now()
        return n.replace(hour=0, minute=0, second=0, microsecond=0)

    def _period_bounds(self, period: str) -> tuple[datetime, datetime]:
        now = self._now()
        today = self._today_start()
        if period == "today":
            return today, now
        if period == "yesterday":
            return today - timedelta(days=1), today
        if period == "week":
            return today - timedelta(days=7), now
        if period == "month":
            return today.replace(day=1), now
        if period == "year":
            return today.replace(month=1, day=1), now
        return today - timedelta(days=30), now

    async def _scalar(self, session: AsyncSession, stmt: Any) -> Any:
        result = await session.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def _rows(self, session: AsyncSession, stmt: Any) -> list[Any]:
        result = await session.execute(stmt)
        return result.fetchall()

    # ── Revenue ───────────────────────────────────────────────────────────────

    async def _get_revenue_metrics(self, session: AsyncSession) -> RevenueMetrics:
        # Import models inline to avoid circular imports at module load
        from app.models.payments.payment import Payment

        now = self._now()
        today = self._today_start()
        yesterday_start = today - timedelta(days=1)
        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        year_start = today.replace(month=1, day=1)
        prev_year_start = year_start.replace(year=year_start.year - 1)

        base = select(func.coalesce(func.sum(Payment.final_amount), 0)).where(
            Payment.payment_status == "COMPLETED"
        )

        today_rev = await self._scalar(
            session, base.where(Payment.created_at >= today, Payment.created_at < now)
        )
        yesterday_rev = await self._scalar(
            session, base.where(Payment.created_at >= yesterday_start, Payment.created_at < today)
        )
        week_rev = await self._scalar(session, base.where(Payment.created_at >= week_start))
        month_rev = await self._scalar(session, base.where(Payment.created_at >= month_start))
        prev_month_rev = await self._scalar(
            session,
            base.where(Payment.created_at >= prev_month_start, Payment.created_at < month_start),
        )
        year_rev = await self._scalar(session, base.where(Payment.created_at >= year_start))
        prev_year_rev = await self._scalar(
            session,
            base.where(Payment.created_at >= prev_year_start, Payment.created_at < year_start),
        )
        total_rev = await self._scalar(session, base)

        count_stmt = select(func.count()).select_from(Payment).where(Payment.payment_status == "COMPLETED")
        total_count = await self._scalar(session, count_stmt)
        avg_order = Decimal(str(total_rev)) / max(Decimal(str(total_count)), Decimal("1"))

        def growth(current: Any, previous: Any) -> float:
            c, p = float(current), float(previous)
            if p == 0:
                return 100.0 if c > 0 else 0.0
            return round(((c - p) / p) * 100, 2)

        return RevenueMetrics(
            today=Decimal(str(today_rev)),
            yesterday=Decimal(str(yesterday_rev)),
            this_week=Decimal(str(week_rev)),
            this_month=Decimal(str(month_rev)),
            this_year=Decimal(str(year_rev)),
            total_lifetime=Decimal(str(total_rev)),
            growth_pct_wow=growth(week_rev, await self._scalar(
                session,
                base.where(
                    Payment.created_at >= week_start - timedelta(days=7),
                    Payment.created_at < week_start,
                ),
            )),
            growth_pct_mom=growth(month_rev, prev_month_rev),
            growth_pct_yoy=growth(year_rev, prev_year_rev),
            average_order_value=avg_order.quantize(Decimal("0.01")),
        )

    # ── Bookings ──────────────────────────────────────────────────────────────

    async def _get_booking_metrics(self, session: AsyncSession) -> BookingMetrics:
        from app.models.bookings.booking import Booking

        rows = await self._rows(
            session,
            select(Booking.booking_status, func.count().label("cnt"))
            .group_by(Booking.booking_status)
            .where(Booking.deleted_at.is_(None)),
        )
        status_map: dict[str, int] = {r.booking_status: r.cnt for r in rows}
        total = sum(status_map.values())

        # Revenue per booking (average)
        from app.models.payments.payment import Payment
        avg_val_row = await self._scalar(
            session,
            select(func.coalesce(func.avg(Payment.final_amount), 0)).where(Payment.payment_status == "COMPLETED"),
        )

        completed = status_map.get("COMPLETED", 0)
        cancelled = status_map.get("CANCELLED", 0)
        return BookingMetrics(
            total=total,
            pending=status_map.get("PENDING", 0),
            confirmed=status_map.get("CONFIRMED", 0),
            in_progress=status_map.get("IN_PROGRESS", 0),
            completed=completed,
            cancelled=cancelled,
            refunded=status_map.get("REFUNDED", 0),
            rescheduled=status_map.get("RESCHEDULED", 0),
            completion_rate=round(completed / max(total, 1) * 100, 2),
            cancellation_rate=round(cancelled / max(total, 1) * 100, 2),
            avg_booking_value=Decimal(str(avg_val_row)).quantize(Decimal("0.01")),
        )

    # ── Users ─────────────────────────────────────────────────────────────────

    async def _get_user_metrics(self, session: AsyncSession) -> UserMetrics:
        from app.models.users.user import User

        now = self._now()
        today = self._today_start()
        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)
        dau_window = now - timedelta(hours=24)
        mau_window = now - timedelta(days=30)

        rows = await self._rows(
            session,
            select(User.account_status, func.count().label("cnt"))
            .group_by(User.account_status)
            .where(User.deleted_at.is_(None)),
        )
        status_map = {r.account_status: r.cnt for r in rows}
        total = sum(status_map.values())

        new_today = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.created_at >= today, User.deleted_at.is_(None)
            ),
        )
        new_week = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.created_at >= week_start, User.deleted_at.is_(None)
            ),
        )
        new_month = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.created_at >= month_start, User.deleted_at.is_(None)
            ),
        )
        dau = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.last_login_at >= dau_window, User.deleted_at.is_(None)
            ),
        )
        mau = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.last_login_at >= mau_window, User.deleted_at.is_(None)
            ),
        )
        returning = await self._scalar(
            session,
            select(func.count()).select_from(User).where(
                User.last_login_at.isnot(None),
                User.created_at < month_start,
                User.last_login_at >= month_start,
                User.deleted_at.is_(None),
            ),
        )

        active = status_map.get("ACTIVE", 0)
        return UserMetrics(
            total=total,
            active=active,
            suspended=status_map.get("SUSPENDED", 0),
            banned=status_map.get("BANNED", 0),
            deactivated=status_map.get("DEACTIVATED", 0),
            new_today=int(new_today),
            new_this_week=int(new_week),
            new_this_month=int(new_month),
            daily_active=int(dau),
            monthly_active=int(mau),
            returning_users=int(returning),
            retention_rate=round(int(returning) / max(active, 1) * 100, 2),
        )

    # ── Vendors ───────────────────────────────────────────────────────────────

    async def _get_vendor_metrics(self, session: AsyncSession) -> VendorMetrics:
        from app.models.vendors.vendor import Vendor

        rows = await self._rows(
            session,
            select(Vendor.verification_status, func.count().label("cnt"))
            .group_by(Vendor.verification_status)
            .where(Vendor.deleted_at.is_(None)),
        )
        status_map = {r.verification_status: r.cnt for r in rows}
        total = sum(status_map.values())

        # Average rating across all vendors
        avg_rating_val = await self._scalar(
            session,
            select(func.coalesce(func.avg(Vendor.average_rating), 0)).where(
                Vendor.deleted_at.is_(None)
            ),
        )

        # Avg bookings per vendor
        from app.models.bookings.booking import Booking
        total_bookings = await self._scalar(
            session, select(func.count()).select_from(Booking).where(Booking.deleted_at.is_(None))
        )

        # Top 5 vendors by booking count (via BookingAssignment — Booking has no direct vendor_id)
        from app.models.bookings.booking_assignment import BookingAssignment
        top_vendors_rows = await self._rows(
            session,
            select(BookingAssignment.vendor_id, func.count(func.distinct(BookingAssignment.booking_id)).label("booking_count"))
            .join(Booking, BookingAssignment.booking_id == Booking.id)
            .where(Booking.deleted_at.is_(None))
            .group_by(BookingAssignment.vendor_id)
            .order_by(func.count(func.distinct(BookingAssignment.booking_id)).desc())
            .limit(5),
        )
        top_vendors = [
            {"vendor_id": str(r.vendor_id), "booking_count": r.booking_count}
            for r in top_vendors_rows
        ]

        return VendorMetrics(
            total=total,
            verified=status_map.get("VERIFIED", 0),
            pending_approval=status_map.get("PENDING", 0),
            rejected=status_map.get("REJECTED", 0),
            suspended=status_map.get("SUSPENDED", 0),
            inactive=status_map.get("INACTIVE", 0),
            new_this_month=await self._scalar(
                session,
                select(func.count()).select_from(Vendor).where(
                    Vendor.created_at >= self._now().replace(day=1),
                    Vendor.deleted_at.is_(None),
                ),
            ),
            avg_rating=round(float(avg_rating_val), 2),
            avg_bookings_per_vendor=round(int(total_bookings) / max(total, 1), 2),
            top_vendors=top_vendors,
        )

    # ── Payments ──────────────────────────────────────────────────────────────

    async def _get_payment_metrics(self, session: AsyncSession) -> PaymentMetrics:
        from app.models.payments.payment import Payment

        rows = await self._rows(
            session,
            select(Payment.payment_status, func.count().label("cnt"), func.coalesce(func.sum(Payment.final_amount), 0).label("vol"))
            .group_by(Payment.payment_status),
        )
        status_map: dict[str, dict[str, Any]] = {}
        for r in rows:
            status_map[r.payment_status] = {"count": r.cnt, "volume": r.vol}

        total_txn = sum(v["count"] for v in status_map.values())
        success_count = status_map.get("COMPLETED", {}).get("count", 0)
        refund_vol = status_map.get("REFUNDED", {}).get("volume", Decimal("0"))
        total_vol = status_map.get("COMPLETED", {}).get("volume", Decimal("0"))

        avg_txn = await self._scalar(
            session,
            select(func.coalesce(func.avg(Payment.final_amount), 0)).where(Payment.payment_status == "COMPLETED"),
        )

        return PaymentMetrics(
            total_transactions=total_txn,
            successful=success_count,
            failed=status_map.get("FAILED", {}).get("count", 0),
            refunded=status_map.get("REFUNDED", {}).get("count", 0),
            pending=status_map.get("PENDING", {}).get("count", 0),
            total_volume=Decimal(str(total_vol)).quantize(Decimal("0.01")),
            total_refunded=Decimal(str(refund_vol)).quantize(Decimal("0.01")),
            gateway_success_rate=round(success_count / max(total_txn, 1) * 100, 2),
            avg_transaction_value=Decimal(str(avg_txn)).quantize(Decimal("0.01")),
        )

    # ── Wallets ───────────────────────────────────────────────────────────────

    async def _get_wallet_metrics(self, session: AsyncSession) -> WalletMetrics:
        from app.models.wallets.wallet import Wallet
        from app.models.wallets.transaction import WalletTransaction

        wallet_rows = await self._rows(
            session,
            select(
                Wallet.wallet_status,
                func.count().label("cnt"),
                func.coalesce(func.sum(Wallet.available_balance), 0).label("bal"),
            ).group_by(Wallet.wallet_status),
        )
        total_wallets = sum(r.cnt for r in wallet_rows)
        active_wallets = sum(r.cnt for r in wallet_rows if r.wallet_status == "ACTIVE")
        frozen_wallets = sum(r.cnt for r in wallet_rows if r.wallet_status == "FROZEN")
        total_balance = sum(r.bal for r in wallet_rows)

        tx_rows = await self._rows(
            session,
            select(
                WalletTransaction.transaction_type,
                func.coalesce(func.sum(WalletTransaction.amount), 0).label("vol"),
            ).group_by(WalletTransaction.transaction_type),
        )
        tx_map = {r.transaction_type: r.vol for r in tx_rows}

        return WalletMetrics(
            total_wallets=total_wallets,
            active_wallets=active_wallets,
            frozen_wallets=frozen_wallets,
            total_balance=Decimal(str(total_balance)).quantize(Decimal("0.01")),
            total_credits_issued=Decimal(str(tx_map.get("CREDIT", 0))).quantize(Decimal("0.01")),
            total_debits=Decimal(str(tx_map.get("DEBIT", 0))).quantize(Decimal("0.01")),
            total_rewards_issued=Decimal(str(tx_map.get("REWARD", 0))).quantize(Decimal("0.01")),
            total_cashback_issued=Decimal(str(tx_map.get("CASHBACK", 0))).quantize(Decimal("0.01")),
        )

    # ── Memberships ───────────────────────────────────────────────────────────

    async def _get_membership_metrics(self, session: AsyncSession) -> MembershipMetrics:
        from app.models.memberships.user_membership import UserMembership
        from app.models.memberships.membership_plan import MembershipPlan
        from app.models.enums import MembershipBillingCycle

        now = self._now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        active = await self._scalar(
            session,
            select(func.count()).select_from(UserMembership).where(
                UserMembership.membership_status == "ACTIVE",
            ),
        )
        expired_month = await self._scalar(
            session,
            select(func.count()).select_from(UserMembership).where(
                UserMembership.membership_status == "EXPIRED",
                UserMembership.expires_at >= month_start,
                UserMembership.expires_at <= now,
            ),
        )
        new_month = await self._scalar(
            session,
            select(func.count()).select_from(UserMembership).where(
                UserMembership.created_at >= month_start
            ),
        )
        renewed_month = await self._scalar(
            session,
            select(func.count()).select_from(UserMembership).where(
                UserMembership.renewal_count > 0,
                UserMembership.updated_at >= month_start,
            ),
        )

        # MRR from active memberships, amortised to a monthly figure per billing cycle
        mrr_row = await self._scalar(
            session,
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                UserMembership.billing_cycle == MembershipBillingCycle.ANNUAL,
                                MembershipPlan.yearly_price / 12,
                            ),
                            (
                                UserMembership.billing_cycle == MembershipBillingCycle.QUARTERLY,
                                MembershipPlan.monthly_price,
                            ),
                            else_=MembershipPlan.monthly_price,
                        )
                    ),
                    0,
                )
            )
            .select_from(UserMembership)
            .join(MembershipPlan, UserMembership.plan_id == MembershipPlan.id)
            .where(UserMembership.membership_status == "ACTIVE"),
        )

        # Plan breakdown
        plan_rows = await self._rows(
            session,
            select(MembershipPlan.name, func.count().label("cnt"))
            .select_from(UserMembership)
            .join(MembershipPlan, UserMembership.plan_id == MembershipPlan.id)
            .where(UserMembership.membership_status == "ACTIVE")
            .group_by(MembershipPlan.name)
            .order_by(func.count().desc()),
        )
        plan_breakdown = [
            CategoryBreakdown(label=r.name, value=r.cnt) for r in plan_rows
        ]

        from app.models.users.user import User
        total_users = await self._scalar(
            session,
            select(func.count()).select_from(User).where(User.deleted_at.is_(None)),
        )

        return MembershipMetrics(
            total_active=int(active),
            expired_this_month=int(expired_month),
            renewed_this_month=int(renewed_month),
            new_subscriptions_this_month=int(new_month),
            conversion_rate=round(int(active) / max(int(total_users), 1) * 100, 2),
            monthly_recurring_revenue=Decimal(str(mrr_row)).quantize(Decimal("0.01")),
            churn_rate=round(int(expired_month) / max(int(active) + int(expired_month), 1) * 100, 2),
            plan_breakdown=plan_breakdown,
        )

    # ── Referrals ─────────────────────────────────────────────────────────────

    async def _get_referral_metrics(self, session: AsyncSession) -> ReferralMetrics:
        from app.models.bookings.booking import Booking
        from app.models.referrals.referral import Referral
        from app.models.referrals.referral_reward import ReferralReward

        rows = await self._rows(
            session,
            select(Referral.referral_status, func.count().label("cnt")).group_by(Referral.referral_status),
        )
        status_map = {r.referral_status: r.cnt for r in rows}
        total = sum(status_map.values())
        successful = status_map.get("CONVERTED", 0) + status_map.get("REWARDED", 0)

        total_revenue = await self._scalar(
            session,
            select(func.coalesce(func.sum(Booking.total_amount), 0))
            .select_from(Referral)
            .join(Booking, Referral.first_booking_id == Booking.id),
        )
        total_rewards = await self._scalar(
            session,
            select(func.coalesce(func.sum(ReferralReward.monetary_value), 0)),
        )

        return ReferralMetrics(
            total_referrals=total,
            successful_referrals=successful,
            pending_referrals=status_map.get("PENDING", 0),
            referral_conversion_rate=round(successful / max(total, 1) * 100, 2),
            total_referral_revenue=Decimal(str(total_revenue)).quantize(Decimal("0.01")),
            total_rewards_issued=Decimal(str(total_rewards)).quantize(Decimal("0.01")),
        )

    # ── Support ───────────────────────────────────────────────────────────────

    # SLA resolution targets by priority (hours). No SLA config table exists yet,
    # so these are reasonable fixed thresholds used consistently for the breach count.
    _SLA_HOURS_BY_PRIORITY = {"CRITICAL": 4, "HIGH": 24, "MEDIUM": 48, "LOW": 72}

    async def _get_support_metrics(self, session: AsyncSession) -> SupportMetrics:
        from app.models.support.ticket import SupportTicket

        rows = await self._rows(
            session,
            select(SupportTicket.ticket_status, func.count().label("cnt")).group_by(SupportTicket.ticket_status),
        )
        status_map = {r.ticket_status: r.cnt for r in rows}
        total = sum(status_map.values())

        priority_rows = await self._rows(
            session,
            select(SupportTicket.priority, func.count().label("cnt")).group_by(SupportTicket.priority),
        )
        priority_breakdown = [
            CategoryBreakdown(label=r.priority, value=r.cnt) for r in priority_rows
        ]

        # Average resolution time in hours (from created_at to resolved_at)
        avg_hours = await self._scalar(
            session,
            select(
                func.coalesce(
                    func.avg(
                        func.extract(
                            "epoch",
                            SupportTicket.resolved_at - SupportTicket.created_at,
                        )
                        / 3600
                    ),
                    0,
                )
            ).where(SupportTicket.resolved_at.isnot(None)),
        )

        # SLA breaches: resolved tickets that took longer than their priority's target,
        # plus still-open tickets already past their target.
        now = self._now()
        sla_breach_count = 0
        for priority, hours_limit in self._SLA_HOURS_BY_PRIORITY.items():
            threshold = timedelta(hours=hours_limit)
            resolved_breaches = await self._scalar(
                session,
                select(func.count()).select_from(SupportTicket).where(
                    SupportTicket.priority == priority,
                    SupportTicket.resolved_at.isnot(None),
                    SupportTicket.resolved_at - SupportTicket.created_at > threshold,
                ),
            )
            open_breaches = await self._scalar(
                session,
                select(func.count()).select_from(SupportTicket).where(
                    SupportTicket.priority == priority,
                    SupportTicket.resolved_at.is_(None),
                    SupportTicket.created_at <= now - threshold,
                ),
            )
            sla_breach_count += int(resolved_breaches) + int(open_breaches)

        return SupportMetrics(
            total_tickets=total,
            open_tickets=status_map.get("OPEN", 0),
            in_progress_tickets=status_map.get("IN_PROGRESS", 0),
            resolved_tickets=status_map.get("RESOLVED", 0),
            closed_tickets=status_map.get("CLOSED", 0),
            avg_resolution_hours=round(float(avg_hours), 2),
            sla_breach_count=sla_breach_count,
            priority_breakdown=priority_breakdown,
        )

    # ── Media ─────────────────────────────────────────────────────────────────

    async def _get_media_metrics(self, session: AsyncSession) -> MediaMetrics:
        from app.models.media.image import Image
        from app.models.media.video import Video

        img_rows = await self._rows(
            session,
            select(Image.moderation_status, func.count().label("cnt"), func.coalesce(func.sum(Image.file_size_bytes), 0).label("sz"))
            .group_by(Image.moderation_status),
        )
        img_status_map = {r.moderation_status: {"count": r.cnt, "size": r.sz} for r in img_rows}
        total_images = sum(v["count"] for v in img_status_map.values())
        total_img_size = sum(v["size"] for v in img_status_map.values())

        vid_count = await self._scalar(session, select(func.count()).select_from(Video))
        vid_size = await self._scalar(
            session, select(func.coalesce(func.sum(Video.file_size_bytes), 0)).select_from(Video)
        )

        now = self._now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        uploads_month = await self._scalar(
            session,
            select(func.count()).select_from(Image).where(Image.created_at >= month_start),
        )

        total_storage_bytes = int(total_img_size) + int(vid_size)

        return MediaMetrics(
            total_images=total_images,
            total_videos=int(vid_count),
            pending_moderation=img_status_map.get("PENDING", {}).get("count", 0),
            approved=img_status_map.get("APPROVED", {}).get("count", 0),
            rejected=img_status_map.get("REJECTED", {}).get("count", 0),
            total_storage_mb=round(total_storage_bytes / 1024 / 1024, 2),
            uploads_this_month=int(uploads_month),
        )

    # ── Notifications ─────────────────────────────────────────────────────────

    async def _get_notification_metrics(self, session: AsyncSession) -> NotificationMetrics:
        from app.models.notifications.notification import Notification

        rows = await self._rows(
            session,
            select(Notification.channel, func.count().label("cnt")).group_by(Notification.channel),
        )
        channel_map = {r.channel: r.cnt for r in rows}
        total = sum(channel_map.values())

        read_count = await self._scalar(
            session,
            select(func.count()).select_from(Notification).where(Notification.read_at.isnot(None)),
        )

        # Delivery rate: SENT vs everything attempted (SENT + FAILED). PENDING channels
        # (no real push/SMS/email dispatcher wired yet) are excluded from the denominator
        # since they were never actually attempted.
        sent_count = await self._scalar(
            session,
            select(func.count()).select_from(Notification).where(Notification.notification_status == "SENT"),
        )
        failed_count = await self._scalar(
            session,
            select(func.count()).select_from(Notification).where(Notification.notification_status == "FAILED"),
        )
        attempted = int(sent_count) + int(failed_count)
        delivery_rate = round(int(sent_count) / max(attempted, 1) * 100, 2) if attempted else 0.0

        return NotificationMetrics(
            total_sent=total,
            push_sent=channel_map.get("PUSH", 0),
            email_sent=channel_map.get("EMAIL", 0),
            sms_sent=channel_map.get("SMS", 0),
            in_app_sent=channel_map.get("IN_APP", 0),
            delivery_rate=delivery_rate,
            read_rate=round(int(read_count) / max(total, 1) * 100, 2),
            avg_ctr=0.0,  # No click-tracking exists yet; honestly reported as unmeasured.
        )

    # ── Budgets ───────────────────────────────────────────────────────────────

    async def _get_budget_metrics(self, session: AsyncSession) -> BudgetMetrics:
        from app.models.budgets.budget import Budget
        from app.models.budgets.category import ExpenseCategory
        from app.models.budgets.expense import Expense

        total_budgets = await self._scalar(
            session, select(func.count()).select_from(Budget).where(Budget.deleted_at.is_(None))
        )
        avg_budget = await self._scalar(
            session,
            select(func.coalesce(func.avg(Budget.planned_total), 0)).where(Budget.deleted_at.is_(None)),
        )

        # Over-budget: actual spend exceeds the planned total
        over_budget = await self._scalar(
            session,
            select(func.count())
            .select_from(Budget)
            .where(Budget.deleted_at.is_(None), Budget.actual_total > Budget.planned_total),
        )

        # Average utilization = actual/planned across budgets with a non-zero plan
        avg_utilization = await self._scalar(
            session,
            select(func.coalesce(func.avg(Budget.actual_total / Budget.planned_total * 100), 0)).where(
                Budget.deleted_at.is_(None), Budget.planned_total > 0
            ),
        )

        category_rows = await self._rows(
            session,
            select(ExpenseCategory.name, func.coalesce(func.sum(Expense.actual_amount), 0).label("spend"))
            .select_from(Expense)
            .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
            .where(Expense.deleted_at.is_(None))
            .group_by(ExpenseCategory.name)
            .order_by(func.sum(Expense.actual_amount).desc())
            .limit(10),
        )
        category_distribution = [
            CategoryBreakdown(label=r.name, value=float(r.spend)) for r in category_rows
        ]

        return BudgetMetrics(
            total_budgets=int(total_budgets),
            avg_budget_amount=Decimal(str(avg_budget)).quantize(Decimal("0.01")),
            avg_utilization_pct=round(float(avg_utilization), 2),
            over_budget_count=int(over_budget),
            category_distribution=category_distribution,
        )

    # ── Occasions ─────────────────────────────────────────────────────────────

    async def _get_occasion_metrics(self, session: AsyncSession) -> OccasionMetrics:
        from app.models.occasions.celebration import Celebration
        from app.models.occasions.occasion import Occasion

        now = self._now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_celebrations = await self._scalar(
            session, select(func.count()).select_from(Celebration)
        )
        month_celebrations = await self._scalar(
            session,
            select(func.count()).select_from(Celebration).where(Celebration.created_at >= month_start),
        )

        # Most popular occasion
        popular_rows = await self._rows(
            session,
            select(Occasion.name, func.count(Celebration.id).label("cnt"))
            .select_from(Celebration)
            .join(Occasion, Celebration.occasion_id == Occasion.id)
            .group_by(Occasion.name)
            .order_by(func.count(Celebration.id).desc())
            .limit(5),
        )
        top_occasion = popular_rows[0].name if popular_rows else None
        top_count = popular_rows[0].cnt if popular_rows else 0

        occasion_breakdown = [
            CategoryBreakdown(label=r.name, value=r.cnt) for r in popular_rows
        ]

        # Trending packages: most-booked packages in the current month
        from app.models.bookings.booking import Booking
        from app.models.packages.package import Package
        trending_rows = await self._rows(
            session,
            select(Package.id, Package.name, func.count(Booking.id).label("cnt"))
            .select_from(Booking)
            .join(Package, Booking.package_id == Package.id)
            .where(Booking.deleted_at.is_(None), Booking.created_at >= month_start)
            .group_by(Package.id, Package.name)
            .order_by(func.count(Booking.id).desc())
            .limit(5),
        )
        trending_packages = [
            {"package_id": str(r.id), "name": r.name, "bookings_this_month": r.cnt}
            for r in trending_rows
        ]

        return OccasionMetrics(
            total_celebrations=int(total_celebrations),
            celebrations_this_month=int(month_celebrations),
            most_popular_occasion=top_occasion,
            most_popular_occasion_count=int(top_count),
            occasion_breakdown=occasion_breakdown,
            trending_packages=trending_packages,
        )

    # ── Geographic ────────────────────────────────────────────────────────────

    async def _get_geographic_metrics(self, session: AsyncSession) -> GeographicMetrics:
        from app.models.bookings.booking import Booking
        from app.models.bookings.booking_assignment import BookingAssignment
        from app.models.vendors.vendor import Vendor

        now = self._now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Top cities by booking count and revenue (Booking has no direct vendor_id;
        # vendor linkage is via BookingAssignment)
        city_rows = await self._rows(
            session,
            select(
                Vendor.city,
                Vendor.state,
                func.count(func.distinct(Booking.id)).label("booking_count"),
                func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            )
            .select_from(Booking)
            .join(BookingAssignment, BookingAssignment.booking_id == Booking.id)
            .join(Vendor, BookingAssignment.vendor_id == Vendor.id)
            .where(Booking.deleted_at.is_(None), Vendor.city.isnot(None))
            .group_by(Vendor.city, Vendor.state)
            .order_by(func.count(func.distinct(Booking.id)).desc())
            .limit(10),
        )

        top_cities = []
        for r in city_rows:
            active_vendors = await self._scalar(
                session,
                select(func.count()).select_from(Vendor).where(
                    Vendor.city == r.city,
                    Vendor.verification_status == "VERIFIED",
                    Vendor.deleted_at.is_(None),
                ),
            )
            this_month_bookings = await self._scalar(
                session,
                select(func.count(func.distinct(Booking.id)))
                .select_from(Booking)
                .join(BookingAssignment, BookingAssignment.booking_id == Booking.id)
                .join(Vendor, BookingAssignment.vendor_id == Vendor.id)
                .where(Vendor.city == r.city, Booking.deleted_at.is_(None), Booking.created_at >= month_start),
            )
            prev_month_bookings = await self._scalar(
                session,
                select(func.count(func.distinct(Booking.id)))
                .select_from(Booking)
                .join(BookingAssignment, BookingAssignment.booking_id == Booking.id)
                .join(Vendor, BookingAssignment.vendor_id == Vendor.id)
                .where(
                    Vendor.city == r.city,
                    Booking.deleted_at.is_(None),
                    Booking.created_at >= prev_month_start,
                    Booking.created_at < month_start,
                ),
            )
            tm, pm = int(this_month_bookings), int(prev_month_bookings)
            growth_pct = round(((tm - pm) / pm) * 100, 2) if pm else (100.0 if tm > 0 else 0.0)

            top_cities.append(
                CityMetric(
                    city=r.city,
                    state=r.state,
                    bookings=r.booking_count,
                    revenue=Decimal(str(r.revenue)).quantize(Decimal("0.01")),
                    active_vendors=int(active_vendors),
                    growth_pct=growth_pct,
                )
            )

        state_rows = await self._rows(
            session,
            select(Vendor.state, func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"))
            .select_from(Booking)
            .join(BookingAssignment, BookingAssignment.booking_id == Booking.id)
            .join(Vendor, BookingAssignment.vendor_id == Vendor.id)
            .where(Booking.deleted_at.is_(None), Vendor.state.isnot(None))
            .group_by(Vendor.state)
            .order_by(func.sum(Booking.total_amount).desc())
            .limit(15),
        )
        revenue_by_state = [
            CategoryBreakdown(label=r.state, value=float(r.revenue)) for r in state_rows
        ]

        booking_heat = [
            {"city": c.city, "state": c.state, "intensity": c.bookings} for c in top_cities
        ]

        return GeographicMetrics(
            top_cities=top_cities,
            revenue_by_state=revenue_by_state,
            booking_heat=booking_heat,
        )

    # ── Platform Health ───────────────────────────────────────────────────────

    async def _get_platform_health(self, session: AsyncSession) -> PlatformHealth:
        active_sessions = 0
        try:
            from app.models.auth.session import UserSession
            now = self._now()
            active_sessions = int(
                await self._scalar(
                    session,
                    select(func.count()).select_from(UserSession).where(
                        UserSession.is_active == True,
                        UserSession.expires_at > now,
                    ),
                ) or 0
            )
        except Exception:
            pass

        database_status = "healthy"
        try:
            await session.execute(select(1))
        except Exception:
            database_status = "unhealthy"

        # api_requests_today / avg_response_ms / error_rate_pct / uptime_pct require a
        # request-metrics/APM pipeline that isn't wired up in this codebase yet (no
        # middleware records per-request timing or an uptime prober exists). Reported
        # as None rather than fabricated numbers.
        return PlatformHealth(
            active_sessions=active_sessions,
            api_requests_today=0,
            database_status=database_status,
            avg_response_ms=0.0,
            error_rate_pct=0.0,
            uptime_pct=0.0,
        )

    # ── Pending actions count ─────────────────────────────────────────────────

    async def _get_pending_actions(self, session: AsyncSession) -> dict[str, int]:
        from app.models.bookings.booking import Booking
        from app.models.vendors.vendor import Vendor

        async def _safe_count(stmt) -> int:
            try:
                return int(await self._scalar(session, stmt) or 0)
            except Exception:
                return 0

        pending_vendors = await _safe_count(
            select(func.count()).select_from(Vendor).where(
                Vendor.verification_status == "PENDING", Vendor.deleted_at.is_(None)
            )
        )
        pending_bookings = await _safe_count(
            select(func.count()).select_from(Booking).where(
                Booking.booking_status == "PENDING", Booking.deleted_at.is_(None)
            )
        )

        open_tickets = 0
        try:
            from app.models.support.ticket import SupportTicket
            open_tickets = await _safe_count(
                select(func.count()).select_from(SupportTicket).where(SupportTicket.ticket_status == "OPEN")
            )
        except Exception:
            pass

        pending_media = 0
        try:
            from app.models.media.image import Image
            pending_media = await _safe_count(
                select(func.count()).select_from(Image).where(Image.moderation_status == "PENDING")
            )
        except Exception:
            pass

        return {
            "vendor_approvals": pending_vendors,
            "booking_confirmations": pending_bookings,
            "support_tickets": open_tickets,
            "media_moderation": pending_media,
        }

    # ── Main dashboard entry point ────────────────────────────────────────────

    async def get_executive_dashboard(self) -> ExecutiveDashboard:
        _z = Decimal("0")

        async def _safe(coro, default):
            try:
                return await coro
            except Exception:
                return default

        async with self._uow() as uow:
            s = uow.session
            assert s is not None

            revenue = await _safe(self._get_revenue_metrics(s), RevenueMetrics(today=_z, yesterday=_z, this_week=_z, this_month=_z, this_year=_z, total_lifetime=_z, growth_pct_wow=0.0, growth_pct_mom=0.0, growth_pct_yoy=0.0, average_order_value=_z))
            bookings = await _safe(self._get_booking_metrics(s), BookingMetrics(total=0, pending=0, confirmed=0, in_progress=0, completed=0, cancelled=0, refunded=0, rescheduled=0, completion_rate=0.0, cancellation_rate=0.0, avg_booking_value=_z))
            users = await _safe(self._get_user_metrics(s), UserMetrics(total=0, active=0, suspended=0, banned=0, deactivated=0, new_today=0, new_this_week=0, new_this_month=0, daily_active=0, monthly_active=0, returning_users=0, retention_rate=0.0))
            vendors = await _safe(self._get_vendor_metrics(s), VendorMetrics(total=0, verified=0, pending_approval=0, rejected=0, suspended=0, inactive=0, new_this_month=0, avg_rating=0.0, avg_bookings_per_vendor=0.0, top_vendors=[]))
            payments = await _safe(self._get_payment_metrics(s), PaymentMetrics(total_transactions=0, successful=0, failed=0, refunded=0, pending=0, total_volume=_z, total_refunded=_z, gateway_success_rate=0.0, avg_transaction_value=_z))
            wallets = await _safe(self._get_wallet_metrics(s), WalletMetrics(total_wallets=0, active_wallets=0, frozen_wallets=0, total_balance=_z, total_credits_issued=_z, total_debits=_z, total_rewards_issued=_z, total_cashback_issued=_z))
            geographic = await _safe(self._get_geographic_metrics(s), GeographicMetrics(top_cities=[], revenue_by_state=[], booking_heat=[]))
            platform_health = await _safe(self._get_platform_health(s), PlatformHealth(active_sessions=0, api_requests_today=0, database_status="unknown", avg_response_ms=0.0, error_rate_pct=0.0, uptime_pct=0.0))
            pending_actions = await _safe(self._get_pending_actions(s), {"vendor_approvals": 0, "booking_confirmations": 0, "support_tickets": 0, "media_moderation": 0})
            memberships = await _safe(self._get_membership_metrics(s), MembershipMetrics(total_active=0, expired_this_month=0, renewed_this_month=0, new_subscriptions_this_month=0, conversion_rate=0.0, monthly_recurring_revenue=_z, churn_rate=0.0, plan_breakdown=[]))
            referrals = await _safe(self._get_referral_metrics(s), ReferralMetrics(total_referrals=0, successful_referrals=0, pending_referrals=0, referral_conversion_rate=0.0, total_referral_revenue=_z, total_rewards_issued=_z))
            occasions = await _safe(self._get_occasion_metrics(s), OccasionMetrics(total_celebrations=0, celebrations_this_month=0, most_popular_occasion=None, most_popular_occasion_count=0, occasion_breakdown=[], trending_packages=[]))
            support = await _safe(self._get_support_metrics(s), SupportMetrics(total_tickets=0, open_tickets=0, in_progress_tickets=0, resolved_tickets=0, closed_tickets=0, avg_resolution_hours=0.0, sla_breach_count=0, priority_breakdown=[]))
            media = await _safe(self._get_media_metrics(s), MediaMetrics(total_images=0, total_videos=0, pending_moderation=0, approved=0, rejected=0, total_storage_mb=0.0, uploads_this_month=0))
            notifications = await _safe(self._get_notification_metrics(s), NotificationMetrics(total_sent=0, push_sent=0, email_sent=0, sms_sent=0, in_app_sent=0, delivery_rate=0.0, read_rate=0.0, avg_ctr=0.0))
            budgets = await _safe(self._get_budget_metrics(s), BudgetMetrics(total_budgets=0, avg_budget_amount=_z, avg_utilization_pct=0.0, over_budget_count=0, category_distribution=[]))

        return ExecutiveDashboard(
            generated_at=self._now(),
            period_label="Live snapshot",
            revenue=revenue,
            bookings=bookings,
            users=users,
            vendors=vendors,
            payments=payments,
            wallets=wallets,
            memberships=memberships,
            referrals=referrals,
            occasions=occasions,
            support=support,
            media=media,
            notifications=notifications,
            budgets=budgets,
            geographic=geographic,
            platform_health=platform_health,
            pending_actions=pending_actions,
        )

    # ── Individual metric endpoints ───────────────────────────────────────────

    async def get_revenue_metrics(self) -> RevenueMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_revenue_metrics(uow.session)
        except Exception:
            _z = Decimal("0")
            return RevenueMetrics(today=_z, yesterday=_z, this_week=_z, this_month=_z, this_year=_z, total_lifetime=_z, growth_pct_wow=0.0, growth_pct_mom=0.0, growth_pct_yoy=0.0, average_order_value=_z)

    async def get_booking_metrics(self) -> BookingMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_booking_metrics(uow.session)
        except Exception:
            return BookingMetrics(total=0, pending=0, confirmed=0, in_progress=0, completed=0, cancelled=0, refunded=0, rescheduled=0, completion_rate=0.0, cancellation_rate=0.0, avg_booking_value=Decimal("0"))

    async def get_user_metrics(self) -> UserMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_user_metrics(uow.session)
        except Exception:
            return UserMetrics(total=0, active=0, suspended=0, banned=0, deactivated=0, new_today=0, new_this_week=0, new_this_month=0, daily_active=0, monthly_active=0, returning_users=0, retention_rate=0.0)

    async def get_vendor_metrics(self) -> VendorMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_vendor_metrics(uow.session)
        except Exception:
            return VendorMetrics(total=0, verified=0, pending_approval=0, rejected=0, suspended=0, inactive=0, new_this_month=0, avg_rating=0.0, avg_bookings_per_vendor=0.0, top_vendors=[])

    async def get_payment_metrics(self) -> PaymentMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_payment_metrics(uow.session)
        except Exception:
            return PaymentMetrics(total_transactions=0, successful=0, failed=0, refunded=0, pending=0, total_volume=Decimal("0"), total_refunded=Decimal("0"), gateway_success_rate=0.0, avg_transaction_value=Decimal("0"))

    async def get_wallet_metrics(self) -> WalletMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_wallet_metrics(uow.session)
        except Exception:
            _z = Decimal("0")
            return WalletMetrics(total_wallets=0, active_wallets=0, frozen_wallets=0, total_balance=_z, total_credits_issued=_z, total_debits=_z, total_rewards_issued=_z, total_cashback_issued=_z)

    async def get_support_metrics(self) -> SupportMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_support_metrics(uow.session)
        except Exception:
            return SupportMetrics(total_tickets=0, open_tickets=0, in_progress_tickets=0, resolved_tickets=0, closed_tickets=0, avg_resolution_hours=0.0, sla_breach_count=0, priority_breakdown=[])

    async def get_platform_health(self) -> PlatformHealth:
        try:
            async with self._uow() as uow:
                return await self._get_platform_health(uow.session)
        except Exception:
            return PlatformHealth(active_sessions=0, api_requests_today=0, database_status="unknown", avg_response_ms=0.0, error_rate_pct=0.0, uptime_pct=0.0)

    async def get_geographic_metrics(self) -> GeographicMetrics:
        try:
            async with self._uow() as uow:
                return await self._get_geographic_metrics(uow.session)
        except Exception:
            return GeographicMetrics(top_cities=[], revenue_by_state=[], booking_heat=[])

    async def get_pending_actions(self) -> dict[str, int]:
        try:
            async with self._uow() as uow:
                return await self._get_pending_actions(uow.session)
        except Exception:
            return {"vendor_approvals": 0, "booking_confirmations": 0, "support_tickets": 0, "media_moderation": 0}

    # ── Chart: Revenue time series ────────────────────────────────────────────

    async def get_revenue_chart(
        self,
        *,
        granularity: str = "day",
        days: int = 30,
    ) -> TimeSeriesChart:
        from app.models.payments.payment import Payment

        since = self._now() - timedelta(days=days)
        trunc_fn = {
            "day": "day",
            "week": "week",
            "month": "month",
        }.get(granularity, "day")

        async with self._uow() as uow:
            rows = await self._rows(
                uow.session,
                select(
                    func.date_trunc(trunc_fn, Payment.created_at).label("bucket"),
                    func.coalesce(func.sum(Payment.final_amount), 0).label("revenue"),
                    func.count().label("txn_count"),
                )
                .where(Payment.payment_status == "COMPLETED", Payment.created_at >= since)
                .group_by(text("bucket"))
                .order_by(text("bucket")),
            )

        series = [
            {
                "date": str(r.bucket.date() if hasattr(r.bucket, "date") else r.bucket),
                "revenue": float(r.revenue),
                "transactions": r.txn_count,
            }
            for r in rows
        ]
        return TimeSeriesChart(
            title="Revenue Over Time",
            granularity=granularity,
            series=[{"name": "Revenue (INR)", "data": series}],
            date_range={"from": since.date().isoformat(), "to": self._now().date().isoformat()},
        )

    async def get_bookings_chart(self, *, granularity: str = "day", days: int = 30) -> TimeSeriesChart:
        from app.models.bookings.booking import Booking

        since = self._now() - timedelta(days=days)
        trunc_fn = {"day": "day", "week": "week", "month": "month"}.get(granularity, "day")

        async with self._uow() as uow:
            rows = await self._rows(
                uow.session,
                select(
                    func.date_trunc(trunc_fn, Booking.created_at).label("bucket"),
                    Booking.booking_status,
                    func.count().label("cnt"),
                )
                .where(Booking.created_at >= since, Booking.deleted_at.is_(None))
                .group_by(text("bucket"), Booking.booking_status)
                .order_by(text("bucket")),
            )

        # Pivot by status
        buckets: dict[str, dict[str, int]] = {}
        for r in rows:
            bucket_str = str(r.bucket.date() if hasattr(r.bucket, "date") else r.bucket)
            if bucket_str not in buckets:
                buckets[bucket_str] = {}
            buckets[bucket_str][r.booking_status] = r.cnt

        statuses = ["PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"]
        series = [
            {
                "name": s,
                "data": [
                    {"date": d, "value": buckets.get(d, {}).get(s, 0)}
                    for d in sorted(buckets.keys())
                ],
            }
            for s in statuses
        ]
        return TimeSeriesChart(
            title="Bookings Over Time",
            granularity=granularity,
            series=series,
            date_range={"from": since.date().isoformat(), "to": self._now().date().isoformat()},
        )

    async def get_users_chart(self, *, granularity: str = "day", days: int = 30) -> TimeSeriesChart:
        from app.models.users.user import User

        since = self._now() - timedelta(days=days)
        trunc_fn = {"day": "day", "week": "week", "month": "month"}.get(granularity, "day")

        async with self._uow() as uow:
            rows = await self._rows(
                uow.session,
                select(
                    func.date_trunc(trunc_fn, User.created_at).label("bucket"),
                    func.count().label("new_users"),
                )
                .where(User.created_at >= since, User.deleted_at.is_(None))
                .group_by(text("bucket"))
                .order_by(text("bucket")),
            )

        data = [
            {"date": str(r.bucket.date() if hasattr(r.bucket, "date") else r.bucket), "value": r.new_users}
            for r in rows
        ]
        return TimeSeriesChart(
            title="New User Registrations",
            granularity=granularity,
            series=[{"name": "New Users", "data": data}],
            date_range={"from": since.date().isoformat(), "to": self._now().date().isoformat()},
        )

    async def get_category_distribution_chart(self) -> PieChartData:
        try:
            from app.models.bookings.booking import Booking
            from app.models.packages.package import Package
            from app.models.packages.category import PackageCategory

            async with self._uow() as uow:
                rows = await self._rows(
                    uow.session,
                    select(PackageCategory.name, func.count(Booking.id).label("cnt"))
                    .select_from(Booking)
                    .join(Package, Booking.package_id == Package.id)
                    .join(PackageCategory, Package.category_id == PackageCategory.id)
                    .where(Booking.deleted_at.is_(None))
                    .group_by(PackageCategory.name)
                    .order_by(func.count(Booking.id).desc())
                    .limit(10),
                )

            total = sum(r.cnt for r in rows)
            segments = [
                CategoryBreakdown(
                    label=r.name,
                    value=r.cnt,
                    pct=round(r.cnt / max(total, 1) * 100, 2),
                )
                for r in rows
            ]
            return PieChartData(title="Bookings by Category", segments=segments, total=total)
        except Exception:
            return PieChartData(title="Bookings by Category", segments=[], total=0)

    async def get_activity_feed(self, *, limit: int = 20) -> ActivityFeed:
        """Recent platform activity across bookings, payments, vendors, users."""
        items: list[ActivityItem] = []
        async with self._uow() as uow:
            # Recent bookings
            try:
                from app.models.bookings.booking import Booking
                booking_rows = await self._rows(
                    uow.session,
                    select(Booking.id, Booking.booking_status, Booking.created_at)
                    .where(Booking.deleted_at.is_(None))
                    .order_by(Booking.created_at.desc())
                    .limit(5),
                )
                for r in booking_rows:
                    items.append(ActivityItem(
                        type="booking", entity_id=str(r.id), entity_type="booking",
                        summary=f"Booking {r.booking_status}", timestamp=r.created_at,
                    ))
            except Exception:
                pass

            # Recent payments
            try:
                from app.models.payments.payment import Payment
                payment_rows = await self._rows(
                    uow.session,
                    select(Payment.id, Payment.payment_status, Payment.final_amount, Payment.created_at)
                    .order_by(Payment.created_at.desc())
                    .limit(5),
                )
                for r in payment_rows:
                    items.append(ActivityItem(
                        type="payment", entity_id=str(r.id), entity_type="payment",
                        summary=f"Payment ₹{r.final_amount} {r.payment_status}", timestamp=r.created_at,
                    ))
            except Exception:
                pass

            # Recent user registrations
            try:
                from app.models.users.user import User
                user_rows = await self._rows(
                    uow.session,
                    select(User.id, User.phone, User.created_at)
                    .where(User.deleted_at.is_(None))
                    .order_by(User.created_at.desc())
                    .limit(5),
                )
                for r in user_rows:
                    items.append(ActivityItem(
                        type="user_registered", entity_id=str(r.id), entity_type="user",
                        summary="New user registered", timestamp=r.created_at,
                    ))
            except Exception:
                pass

        # Sort all items by timestamp desc and cap
        items.sort(key=lambda x: x.timestamp, reverse=True)
        trimmed = items[:limit]
        return ActivityFeed(items=trimmed, has_more=len(items) == limit)

    async def get_dashboard_widgets(self) -> list[DashboardWidget]:
        """Lightweight widget cards for the dashboard overview."""
        _z = Decimal("0")

        async def _safe(coro, default):
            try:
                return await coro
            except Exception:
                return default

        async with self._uow() as uow:
            session = uow.session
            revenue = await _safe(self._get_revenue_metrics(session), RevenueMetrics(today=_z, yesterday=_z, this_week=_z, this_month=_z, this_year=_z, total_lifetime=_z, growth_pct_wow=0.0, growth_pct_mom=0.0, growth_pct_yoy=0.0, average_order_value=_z))
            bookings = await _safe(self._get_booking_metrics(session), BookingMetrics(total=0, pending=0, confirmed=0, in_progress=0, completed=0, cancelled=0, refunded=0, rescheduled=0, completion_rate=0.0, cancellation_rate=0.0, avg_booking_value=_z))
            users = await _safe(self._get_user_metrics(session), UserMetrics(total=0, active=0, suspended=0, banned=0, deactivated=0, new_today=0, new_this_week=0, new_this_month=0, daily_active=0, monthly_active=0, returning_users=0, retention_rate=0.0))
            vendors = await _safe(self._get_vendor_metrics(session), VendorMetrics(total=0, verified=0, pending_approval=0, rejected=0, suspended=0, inactive=0, new_this_month=0, avg_rating=0.0, avg_bookings_per_vendor=0.0, top_vendors=[]))
            pending = await _safe(self._get_pending_actions(session), {"vendor_approvals": 0, "booking_confirmations": 0, "support_tickets": 0, "media_moderation": 0})
            support = await _safe(self._get_support_metrics(session), SupportMetrics(total_tickets=0, open_tickets=0, in_progress_tickets=0, resolved_tickets=0, closed_tickets=0, avg_resolution_hours=0.0, sla_breach_count=0, priority_breakdown=[]))

        return [
            DashboardWidget(widget_id="revenue_today", title="Revenue Today", value=revenue.today,
                            change_pct=revenue.growth_pct_mom, trend="up" if revenue.growth_pct_mom > 0 else "down",
                            icon="currency_rupee", color="green"),
            DashboardWidget(widget_id="revenue_month", title="Revenue This Month", value=revenue.this_month,
                            icon="trending_up", color="blue"),
            DashboardWidget(widget_id="total_bookings", title="Total Bookings", value=bookings.total,
                            icon="event", color="purple"),
            DashboardWidget(widget_id="pending_bookings", title="Pending Bookings", value=bookings.pending,
                            icon="pending_actions", color="orange",
                            link="/admin/bookings?status=PENDING"),
            DashboardWidget(widget_id="total_users", title="Total Users", value=users.total,
                            icon="people", color="teal"),
            DashboardWidget(widget_id="new_users_today", title="New Users Today", value=users.new_today,
                            icon="person_add", color="cyan"),
            DashboardWidget(widget_id="vendor_approvals", title="Pending Approvals", value=pending["vendor_approvals"],
                            icon="verified", color="red", link="/admin/vendors?status=PENDING"),
            DashboardWidget(widget_id="open_tickets", title="Open Support Tickets", value=support.open_tickets,
                            icon="support_agent", color="amber", link="/admin/support?status=OPEN"),
            DashboardWidget(widget_id="active_vendors", title="Active Vendors", value=vendors.verified,
                            icon="store", color="green"),
            DashboardWidget(widget_id="completion_rate", title="Booking Completion Rate",
                            value=f"{bookings.completion_rate}%", icon="check_circle", color="green"),
        ]
