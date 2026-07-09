"""
Unit of Work — wraps a single AsyncSession in one transactional boundary.

Usage:
    async with UnitOfWork() as uow:
        user = await uow.users.users.find_by_phone("+919876543210")
        wallet = await uow.wallets.wallets.find_by_user(user.id)
        # commit is called automatically on clean exit
        # rollback is called automatically on exception

Repositories are lazy-initialized on first access via properties.
All repositories share the same AsyncSession, so they participate in one
transaction and see each other's unflushed writes.
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.admin_repository import AdminRepositoryAggregate
from app.repositories.auth_repository import AuthRepository
from app.repositories.booking_repository import BookingRepositoryAggregate
from app.repositories.budget_repository import BudgetRepositoryAggregate
from app.repositories.cms_repository import CMSRepositoryAggregate
from app.repositories.common_repository import CommonRepositoryAggregate
from app.repositories.feedback_repository import FeedbackRepositoryAggregate
from app.repositories.media_repository import MediaRepositoryAggregate
from app.repositories.membership_repository import MembershipRepositoryAggregate
from app.repositories.notification_repository import NotificationRepositoryAggregate
from app.repositories.occasion_repository import OccasionRepositoryAggregate
from app.repositories.package_repository import PackageRepositoryAggregate
from app.repositories.payment_repository import PaymentRepositoryAggregate
from app.repositories.referral_repository import ReferralRepositoryAggregate
from app.repositories.support_repository import SupportRepositoryAggregate
from app.repositories.user_repository import UserRepositoryAggregate
from app.repositories.vendor_repository import VendorRepositoryAggregate
from app.repositories.wallet_repository import WalletRepositoryAggregate


class UnitOfWork:
    """
    Async context manager that owns one database session and exposes all
    domain repositories through lazy-initialized properties.

    The session is committed when the context exits without an exception
    and rolled back if any exception propagates out of the block.

    Args:
        session_factory: Callable that returns an AsyncSession.
                         Defaults to the project AsyncSessionLocal factory.
                         Override in tests to inject a fixture session.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

        # Lazy repository references — None until first access
        self._auth: AuthRepository | None = None
        self._users: UserRepositoryAggregate | None = None
        self._vendors: VendorRepositoryAggregate | None = None
        self._occasions: OccasionRepositoryAggregate | None = None
        self._packages: PackageRepositoryAggregate | None = None
        self._bookings: BookingRepositoryAggregate | None = None
        self._payments: PaymentRepositoryAggregate | None = None
        self._wallets: WalletRepositoryAggregate | None = None
        self._memberships: MembershipRepositoryAggregate | None = None
        self._notifications: NotificationRepositoryAggregate | None = None
        self._support: SupportRepositoryAggregate | None = None
        self._feedback: FeedbackRepositoryAggregate | None = None
        self._media: MediaRepositoryAggregate | None = None
        self._referrals: ReferralRepositoryAggregate | None = None
        self._budgets: BudgetRepositoryAggregate | None = None
        self._admin: AdminRepositoryAggregate | None = None
        self._common: CommonRepositoryAggregate | None = None
        self._cms: CMSRepositoryAggregate | None = None

    # ── Context Manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.close()

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def flush(self) -> None:
        if self.session is not None:
            await self.session.flush()

    # ── Repository Properties ─────────────────────────────────────────────────

    @property
    def auth(self) -> AuthRepository:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._auth is None:
            self._auth = AuthRepository(self.session)
        return self._auth

    @property
    def users(self) -> UserRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._users is None:
            self._users = UserRepositoryAggregate(self.session)
        return self._users

    @property
    def vendors(self) -> VendorRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._vendors is None:
            self._vendors = VendorRepositoryAggregate(self.session)
        return self._vendors

    @property
    def occasions(self) -> OccasionRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._occasions is None:
            self._occasions = OccasionRepositoryAggregate(self.session)
        return self._occasions

    @property
    def packages(self) -> PackageRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._packages is None:
            self._packages = PackageRepositoryAggregate(self.session)
        return self._packages

    @property
    def bookings(self) -> BookingRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._bookings is None:
            self._bookings = BookingRepositoryAggregate(self.session)
        return self._bookings

    @property
    def payments(self) -> PaymentRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._payments is None:
            self._payments = PaymentRepositoryAggregate(self.session)
        return self._payments

    @property
    def wallets(self) -> WalletRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._wallets is None:
            self._wallets = WalletRepositoryAggregate(self.session)
        return self._wallets

    @property
    def memberships(self) -> MembershipRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._memberships is None:
            self._memberships = MembershipRepositoryAggregate(self.session)
        return self._memberships

    @property
    def notifications(self) -> NotificationRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._notifications is None:
            self._notifications = NotificationRepositoryAggregate(self.session)
        return self._notifications

    @property
    def support(self) -> SupportRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._support is None:
            self._support = SupportRepositoryAggregate(self.session)
        return self._support

    @property
    def feedback(self) -> FeedbackRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._feedback is None:
            self._feedback = FeedbackRepositoryAggregate(self.session)
        return self._feedback

    @property
    def media(self) -> MediaRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._media is None:
            self._media = MediaRepositoryAggregate(self.session)
        return self._media

    @property
    def referrals(self) -> ReferralRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._referrals is None:
            self._referrals = ReferralRepositoryAggregate(self.session)
        return self._referrals

    @property
    def budgets(self) -> BudgetRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._budgets is None:
            self._budgets = BudgetRepositoryAggregate(self.session)
        return self._budgets

    @property
    def admin(self) -> AdminRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._admin is None:
            self._admin = AdminRepositoryAggregate(self.session)
        return self._admin

    @property
    def common(self) -> CommonRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._common is None:
            self._common = CommonRepositoryAggregate(self.session)
        return self._common

    @property
    def cms(self) -> CMSRepositoryAggregate:
        assert self.session is not None, "UnitOfWork must be used as an async context manager."
        if self._cms is None:
            self._cms = CMSRepositoryAggregate(self.session)
        return self._cms
