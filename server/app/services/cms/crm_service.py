"""
CRM Service — 360° Vendor & Customer Profiles
=============================================
Aggregates data across all domain tables for a complete relationship view.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.cms.crm import (
    CustomerCRMProfile,
    CustomerCRMSummary,
    CustomerFinancials,
    PerformanceMonth,
    TimelineEvent,
    VendorCRMProfile,
    VendorCRMSummary,
    VendorFinancials,
    VendorKYC,
    VendorRatings,
)
from app.services.base import BaseService


class CRMService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Vendor CRM ────────────────────────────────────────────────────────────

    async def get_vendor_crm_profile(self, vendor_id: uuid.UUID) -> VendorCRMProfile:
        async with self._uow() as uow:
            session = uow.session
            assert session is not None

            from app.models.bookings.booking import Booking
            from app.models.payments.payment import Payment
            from app.models.vendors.vendor import Vendor
            from app.models.vendors.vendor_document import VendorDocument
            from app.models.vendors.vendor_review import VendorReview
            from app.models.wallets.wallet import Wallet

            # Core vendor record
            vendor_row = (
                await session.execute(
                    select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
                )
            ).scalar_one_or_none()

            if vendor_row is None:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

            summary = VendorCRMSummary(
                vendor_id=vendor_row.id,
                business_name=vendor_row.business_name,
                phone=getattr(vendor_row, "phone", None),
                email=getattr(vendor_row, "email", None),
                city=getattr(vendor_row, "city", None),
                state=getattr(vendor_row, "state", None),
                verification_status=str(vendor_row.verification_status),
                account_status=str(getattr(vendor_row, "account_status", "ACTIVE")),
                onboarded_at=vendor_row.created_at,
            )

            # KYC / Documents
            doc_rows = (
                await session.execute(
                    select(VendorDocument).where(
                        VendorDocument.vendor_id == vendor_id,
                        VendorDocument.deleted_at.is_(None),
                    )
                )
            ).scalars().all()

            kyc = VendorKYC(
                kyc_status=str(vendor_row.verification_status),
                documents=[
                    {
                        "id": str(d.id),
                        "type": d.document_type,
                        "number": getattr(d, "document_number", None),
                        "status": getattr(d, "verification_status", "PENDING"),
                    }
                    for d in doc_rows
                ],
                certificates=[],
            )

            # Financial aggregation
            booking_agg = (
                await session.execute(
                    select(
                        func.count().label("total"),
                        func.sum(
                            func.case((Booking.status == "COMPLETED", 1), else_=0)
                        ).label("completed"),
                        func.sum(
                            func.case((Booking.status == "CANCELLED", 1), else_=0)
                        ).label("cancelled"),
                        func.coalesce(func.sum(Booking.total_amount), 0).label("total_rev"),
                    ).where(Booking.vendor_id == vendor_id, Booking.deleted_at.is_(None))
                )
            ).one()

            wallet_balance = (
                await session.execute(
                    select(func.coalesce(Wallet.balance, 0)).where(
                        Wallet.user_id == getattr(vendor_row, "user_id", None)
                    )
                )
            ).scalar_one_or_none() or Decimal("0")

            financials = VendorFinancials(
                total_revenue_lifetime=Decimal(str(booking_agg.total_rev)).quantize(Decimal("0.01")),
                revenue_this_month=Decimal("0"),
                revenue_last_month=Decimal("0"),
                total_bookings=int(booking_agg.total or 0),
                completed_bookings=int(booking_agg.completed or 0),
                cancelled_bookings=int(booking_agg.cancelled or 0),
                avg_booking_value=(
                    Decimal(str(booking_agg.total_rev)) / max(Decimal(str(booking_agg.total or 1)), Decimal("1"))
                ).quantize(Decimal("0.01")),
                commission_earned_platform=Decimal("0"),
                pending_settlement=Decimal("0"),
                wallet_balance=Decimal(str(wallet_balance)).quantize(Decimal("0.01")),
                settlement_history=[],
            )

            # Ratings
            review_agg = (
                await session.execute(
                    select(
                        func.coalesce(func.avg(VendorReview.rating), 0).label("avg_rating"),
                        func.count().label("total_reviews"),
                    ).where(VendorReview.vendor_id == vendor_id)
                )
            ).one()

            dist_rows = (
                await session.execute(
                    select(VendorReview.rating, func.count().label("cnt"))
                    .where(VendorReview.vendor_id == vendor_id)
                    .group_by(VendorReview.rating)
                )
            ).fetchall()
            rating_dist = {str(r.rating): r.cnt for r in dist_rows}

            ratings = VendorRatings(
                avg_rating=round(float(review_agg.avg_rating), 2),
                total_reviews=int(review_agg.total_reviews),
                rating_distribution=rating_dist,
                recent_reviews=[],
            )

            # Monthly performance (last 6 months)
            monthly_rows = (
                await session.execute(
                    select(
                        func.date_trunc("month", Booking.created_at).label("month"),
                        func.count().label("cnt"),
                        func.coalesce(func.sum(Booking.total_amount), 0).label("rev"),
                    )
                    .where(Booking.vendor_id == vendor_id, Booking.deleted_at.is_(None))
                    .group_by(func.date_trunc("month", Booking.created_at))
                    .order_by(func.date_trunc("month", Booking.created_at).desc())
                    .limit(6)
                )
            ).fetchall()

            monthly_perf = [
                PerformanceMonth(
                    year=r.month.year,
                    month=r.month.month,
                    label=r.month.strftime("%b %Y"),
                    bookings=r.cnt,
                    revenue=Decimal(str(r.rev)).quantize(Decimal("0.01")),
                    completion_rate=0.0,
                    cancellation_rate=0.0,
                )
                for r in monthly_rows
            ]

            # Recent bookings (last 5)
            recent_booking_rows = (
                await session.execute(
                    select(Booking.id, Booking.status, Booking.total_amount, Booking.created_at)
                    .where(Booking.vendor_id == vendor_id, Booking.deleted_at.is_(None))
                    .order_by(Booking.created_at.desc())
                    .limit(5)
                )
            ).fetchall()

            recent_bookings = [
                {
                    "id": str(r.id),
                    "status": r.status,
                    "amount": str(r.total_amount),
                    "date": r.created_at.isoformat(),
                }
                for r in recent_booking_rows
            ]

        return VendorCRMProfile(
            summary=summary,
            kyc=kyc,
            financials=financials,
            ratings=ratings,
            bank_accounts=[],
            monthly_performance=monthly_perf,
            recent_bookings=recent_bookings,
            timeline=[
                TimelineEvent(
                    event_type="vendor_registered",
                    title="Vendor Registered",
                    timestamp=vendor_row.created_at,
                ),
            ],
            notes=None,
            tags=[],
            verification_timeline=[],
        )

    # ── Customer CRM ──────────────────────────────────────────────────────────

    async def get_customer_crm_profile(self, user_id: uuid.UUID) -> CustomerCRMProfile:
        async with self._uow() as uow:
            session = uow.session
            assert session is not None

            from app.models.bookings.booking import Booking
            from app.models.payments.payment import Payment
            from app.models.support.ticket import SupportTicket
            from app.models.users.address import UserAddress
            from app.models.users.user import User
            from app.models.wallets.wallet import Wallet

            user_row = (
                await session.execute(
                    select(User).where(User.id == user_id, User.deleted_at.is_(None))
                )
            ).scalar_one_or_none()

            if user_row is None:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            summary = CustomerCRMSummary(
                user_id=user_row.id,
                full_name=getattr(user_row, "full_name", None),
                phone=user_row.phone,
                email=getattr(user_row, "email", None),
                account_status=str(user_row.account_status),
                registered_at=user_row.created_at,
                last_login_at=getattr(user_row, "last_login_at", None),
            )

            # Financial summary
            booking_agg = (
                await session.execute(
                    select(
                        func.count().label("total"),
                        func.sum(
                            func.case((Booking.status == "COMPLETED", 1), else_=0)
                        ).label("completed"),
                        func.sum(
                            func.case((Booking.status == "CANCELLED", 1), else_=0)
                        ).label("cancelled"),
                        func.coalesce(func.sum(Booking.total_amount), 0).label("total_spent"),
                        func.coalesce(func.avg(Booking.total_amount), 0).label("avg_value"),
                    ).where(Booking.customer_id == user_id, Booking.deleted_at.is_(None))
                )
            ).one()

            wallet_row = (
                await session.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                )
            ).scalar_one_or_none()

            financials = CustomerFinancials(
                total_spent_lifetime=Decimal(str(booking_agg.total_spent)).quantize(Decimal("0.01")),
                spent_this_month=Decimal("0"),
                total_bookings=int(booking_agg.total or 0),
                completed_bookings=int(booking_agg.completed or 0),
                cancelled_bookings=int(booking_agg.cancelled or 0),
                avg_booking_value=Decimal(str(booking_agg.avg_value)).quantize(Decimal("0.01")),
                wallet_balance=Decimal(str(getattr(wallet_row, "balance", 0) or 0)).quantize(Decimal("0.01")),
                reward_points=Decimal(str(getattr(wallet_row, "reward_balance", 0) or 0)),
                total_refunds_received=Decimal("0"),
            )

            # Addresses
            addr_rows = (
                await session.execute(
                    select(UserAddress).where(
                        UserAddress.user_id == user_id, UserAddress.is_active == True
                    )
                )
            ).scalars().all()

            addresses = [
                {
                    "id": str(a.id),
                    "label": a.label,
                    "city": a.city,
                    "is_default": a.is_default,
                }
                for a in addr_rows
            ]

            # Open tickets
            open_tickets_count = (
                await session.execute(
                    select(func.count()).select_from(SupportTicket).where(
                        SupportTicket.user_id == user_id,
                        SupportTicket.status.in_(["OPEN", "IN_PROGRESS"]),
                    )
                )
            ).scalar_one_or_none() or 0

            # Recent bookings
            recent_bookings_rows = (
                await session.execute(
                    select(Booking.id, Booking.status, Booking.total_amount, Booking.created_at)
                    .where(Booking.customer_id == user_id, Booking.deleted_at.is_(None))
                    .order_by(Booking.created_at.desc())
                    .limit(5)
                )
            ).fetchall()

            recent_bookings = [
                {
                    "id": str(r.id),
                    "status": r.status,
                    "amount": str(r.total_amount),
                    "date": r.created_at.isoformat(),
                }
                for r in recent_bookings_rows
            ]

        return CustomerCRMProfile(
            summary=summary,
            financials=financials,
            active_membership=None,
            recent_bookings=recent_bookings,
            recent_payments=[],
            addresses=addresses,
            referral_stats={},
            open_support_tickets=int(open_tickets_count),
            recent_notifications=[],
            recent_reviews=[],
            timeline=[
                TimelineEvent(
                    event_type="user_registered",
                    title="Account Created",
                    timestamp=user_row.created_at,
                )
            ],
        )

    # ── Vendor list (paginated CRM view) ──────────────────────────────────────

    async def list_vendors_crm(
        self,
        *,
        verification_status: str | None = None,
        city: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        from sqlalchemy import or_
        from app.models.vendors.vendor import Vendor

        async with self._uow() as uow:
            conditions = [Vendor.deleted_at.is_(None)]
            if verification_status:
                conditions.append(Vendor.verification_status == verification_status)
            if city:
                conditions.append(Vendor.city.ilike(f"%{city}%"))
            if search:
                conditions.append(
                    or_(
                        Vendor.business_name.ilike(f"%{search}%"),
                        Vendor.legal_name.ilike(f"%{search}%"),
                    )
                )

            count_stmt = select(func.count()).select_from(Vendor).where(*conditions)
            data_stmt = (
                select(Vendor).where(*conditions).order_by(Vendor.created_at.desc()).offset(skip).limit(limit)
            )
            total = (await uow.session.execute(count_stmt)).scalar_one()
            rows = (await uow.session.execute(data_stmt)).scalars().all()

            result = [
                {
                    "id": str(v.id),
                    "business_name": v.business_name,
                    "city": getattr(v, "city", None),
                    "verification_status": str(v.verification_status),
                    "avg_rating": float(getattr(v, "average_rating", 0) or 0),
                    "created_at": v.created_at.isoformat(),
                }
                for v in rows
            ]

        return result, total

    async def list_customers_crm(
        self,
        *,
        account_status: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        from sqlalchemy import or_
        from app.models.users.user import User

        async with self._uow() as uow:
            conditions = [User.deleted_at.is_(None)]
            if account_status:
                conditions.append(User.account_status == account_status)
            if search:
                conditions.append(
                    or_(
                        User.full_name.ilike(f"%{search}%"),
                        User.phone.ilike(f"%{search}%"),
                    )
                )

            count_stmt = select(func.count()).select_from(User).where(*conditions)
            data_stmt = (
                select(User).where(*conditions).order_by(User.created_at.desc()).offset(skip).limit(limit)
            )
            total = (await uow.session.execute(count_stmt)).scalar_one()
            rows = (await uow.session.execute(data_stmt)).scalars().all()

            result = [
                {
                    "id": str(u.id),
                    "full_name": getattr(u, "full_name", None),
                    "phone": u.phone,
                    "account_status": str(u.account_status),
                    "created_at": u.created_at.isoformat(),
                }
                for u in rows
            ]

        return result, total
