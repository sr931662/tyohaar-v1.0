"""
Core dependency providers for the Tyohaar API.

Every injectable object that a route handler may need is defined here:
  - UnitOfWork (transactional boundary)
  - All 16 domain services

Rules
-----
- No business logic. No repository logic. No CRUD.
- Each service factory returns a *new* service instance per call.
  Services themselves open a fresh UoW per operation (see BaseService._uow).
- Typed Annotated aliases (XxxDep) give routes a one-import experience.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from app.db.session import AsyncSessionLocal
from app.repositories.unit_of_work import UnitOfWork
from app.services.admin.service import AdminService
from app.services.auth.service import AuthService
from app.services.bookings.service import BookingService
from app.services.budgets.service import BudgetService
from app.services.common.service import CommonService
from app.services.media.service import MediaService
from app.services.memberships.service import MembershipService
from app.services.notifications.service import NotificationService
from app.services.occasions.service import OccasionService
from app.services.packages.service import PackageService
from app.services.payments.service import PaymentService
from app.services.referrals.service import ReferralService
from app.services.support.service import SupportService
from app.services.users.service import UserService
from app.services.vendors.service import VendorService
from app.services.wallets.service import WalletService


# ── Unit of Work ──────────────────────────────────────────────────────────────

async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    Dependency — yields a request-scoped UnitOfWork.

    All repository access within a single route handler shares one transaction.
    Committed automatically on clean exit; rolled back on any exception.
    """
    async with UnitOfWork() as uow:
        yield uow


UoWDep = Annotated[UnitOfWork, Depends(get_uow)]


# ── Service factories ─────────────────────────────────────────────────────────

def get_auth_service() -> AuthService:
    """Dependency factory — returns an AuthService bound to the default session factory."""
    return AuthService(AsyncSessionLocal)


def get_user_service() -> UserService:
    """Dependency factory — returns a UserService bound to the default session factory."""
    return UserService(AsyncSessionLocal)


def get_vendor_service() -> VendorService:
    """Dependency factory — returns a VendorService bound to the default session factory."""
    return VendorService(AsyncSessionLocal)


def get_occasion_service() -> OccasionService:
    """Dependency factory — returns an OccasionService bound to the default session factory."""
    return OccasionService(AsyncSessionLocal)


def get_package_service() -> PackageService:
    """Dependency factory — returns a PackageService bound to the default session factory."""
    return PackageService(AsyncSessionLocal)


def get_booking_service() -> BookingService:
    """Dependency factory — returns a BookingService bound to the default session factory."""
    return BookingService(AsyncSessionLocal)


def get_payment_service() -> PaymentService:
    """Dependency factory — returns a PaymentService bound to the default session factory."""
    return PaymentService(AsyncSessionLocal)


def get_wallet_service() -> WalletService:
    """Dependency factory — returns a WalletService bound to the default session factory."""
    return WalletService(AsyncSessionLocal)


def get_membership_service() -> MembershipService:
    """Dependency factory — returns a MembershipService bound to the default session factory."""
    return MembershipService(AsyncSessionLocal)


def get_notification_service() -> NotificationService:
    """Dependency factory — returns a NotificationService bound to the default session factory."""
    return NotificationService(AsyncSessionLocal)


def get_support_service() -> SupportService:
    """Dependency factory — returns a SupportService bound to the default session factory."""
    return SupportService(AsyncSessionLocal)


def get_media_service() -> MediaService:
    """Dependency factory — returns a MediaService bound to the default session factory."""
    return MediaService(AsyncSessionLocal)


def get_referral_service() -> ReferralService:
    """Dependency factory — returns a ReferralService bound to the default session factory."""
    return ReferralService(AsyncSessionLocal)


def get_budget_service() -> BudgetService:
    """Dependency factory — returns a BudgetService bound to the default session factory."""
    return BudgetService(AsyncSessionLocal)


def get_admin_service() -> AdminService:
    """Dependency factory — returns an AdminService bound to the default session factory."""
    return AdminService(AsyncSessionLocal)


def get_common_service() -> CommonService:
    """Dependency factory — returns a CommonService bound to the default session factory."""
    return CommonService(AsyncSessionLocal)


# ── Typed dependency aliases ──────────────────────────────────────────────────
# Use these in route signatures for a single-import, self-documenting API.

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
VendorServiceDep = Annotated[VendorService, Depends(get_vendor_service)]
OccasionServiceDep = Annotated[OccasionService, Depends(get_occasion_service)]
PackageServiceDep = Annotated[PackageService, Depends(get_package_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
WalletServiceDep = Annotated[WalletService, Depends(get_wallet_service)]
MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
SupportServiceDep = Annotated[SupportService, Depends(get_support_service)]
MediaServiceDep = Annotated[MediaService, Depends(get_media_service)]
ReferralServiceDep = Annotated[ReferralService, Depends(get_referral_service)]
BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
CommonServiceDep = Annotated[CommonService, Depends(get_common_service)]
