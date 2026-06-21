"""
User repository — User, UserProfile, UserAddress, UserDevice.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import AccountStatus, UserRole, VerificationStatus
from app.models.users.address import UserAddress
from app.models.users.device import UserDevice
from app.models.users.profile import UserProfile
from app.models.users.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    # ── Lookup ────────────────────────────────────────────────────────────────

    async def find_by_phone(self, phone: str) -> User | None:
        return await self.find_one(User.phone == phone)

    async def find_by_email(self, email: str) -> User | None:
        return await self.find_one(User.email == email)

    async def find_by_username(self, username: str) -> User | None:
        return await self.find_one(User.username == username)

    async def find_by_phone_or_email(self, identifier: str) -> User | None:
        from sqlalchemy import or_
        return await self.find_one(
            or_(User.phone == identifier, User.email == identifier)
        )

    # ── Filters ───────────────────────────────────────────────────────────────

    async def find_by_role(
        self,
        role: UserRole,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(User.role == role, skip=skip, limit=limit)

    async def find_active(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.find_many(
            User.account_status == AccountStatus.ACTIVE,
            skip=skip,
            limit=limit,
        )

    async def find_by_status(
        self,
        status: AccountStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(User.account_status == status, skip=skip, limit=limit)

    # ── Eager Loading ─────────────────────────────────────────────────────────

    async def get_with_profile(self, user_id: uuid.UUID) -> User | None:
        return await self.get_by_id(
            user_id,
            options=[selectinload(User.profile)],
        )

    async def get_with_addresses(self, user_id: uuid.UUID) -> User | None:
        return await self.get_by_id(
            user_id,
            options=[selectinload(User.addresses)],
        )

    async def get_with_devices(self, user_id: uuid.UUID) -> User | None:
        return await self.get_by_id(
            user_id,
            options=[selectinload(User.devices)],
        )

    # ── Account Management ────────────────────────────────────────────────────

    async def update_last_login(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        from datetime import datetime, timezone
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(tz=timezone.utc), last_login_ip=ip_address)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def increment_failed_login(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_count=User.failed_login_count + 1)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def reset_failed_login(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_count=0)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def count_by_role(self) -> dict[str, int]:
        from sqlalchemy import func
        stmt = (
            select(User.role, func.count().label("count"))
            .where(User.deleted_at.is_(None))
            .group_by(User.role)
        )
        result = await self._session.execute(stmt)
        return {str(row.role): row.count for row in result.all()}

    # ── Verification / Lock ───────────────────────────────────────────────────

    async def find_verified(
        self,
        *,
        require_phone: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        filters: list[Any] = [User.account_status == AccountStatus.ACTIVE]
        if require_phone:
            filters.append(User.phone_verified == True)  # noqa: E712
        else:
            filters.append(
                or_(User.phone_verified == True, User.email_verified == True)  # noqa: E712
            )
        return await self.find_many(*filters, skip=skip, limit=limit)

    async def find_locked(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            User.account_locked_until.is_not(None),
            User.account_locked_until > now,
            skip=skip,
            limit=limit,
        )

    async def find_unverified_phone(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(
            User.phone_verified == False,  # noqa: E712
            User.account_status == AccountStatus.PENDING_VERIFICATION,
            skip=skip,
            limit=limit,
        )

    # ── Date Range ────────────────────────────────────────────────────────────

    async def find_by_created_range(
        self,
        start: datetime,
        end: datetime,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(
            User.created_at >= start,
            User.created_at <= end,
            order_by=User.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_last_login_range(
        self,
        start: datetime,
        end: datetime,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(
            User.last_login_at >= start,
            User.last_login_at <= end,
            order_by=User.last_login_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[User]:
        """Case-insensitive search across phone, email, full_name, first_name, username."""
        pattern = f"%{query}%"
        return await self.find_many(
            or_(
                User.phone.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                User.first_name.ilike(pattern),
                User.username.ilike(pattern),
            ),
            order_by=User.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Location (via UserProfile join) ───────────────────────────────────────

    async def find_by_city(
        self,
        city: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        stmt = (
            select(User)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.deleted_at.is_(None))
            .where(User.account_status == AccountStatus.ACTIVE)
            .where(UserProfile.city.ilike(city))
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_state(
        self,
        state: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        stmt = (
            select(User)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.deleted_at.is_(None))
            .where(User.account_status == AccountStatus.ACTIVE)
            .where(UserProfile.state.ilike(state))
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Soft-deleted ──────────────────────────────────────────────────────────

    async def find_soft_deleted(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(
            include_deleted=True,
            skip=skip,
            limit=limit,
        )

    async def find_recently_deleted(
        self,
        since: datetime,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await self.find_many(
            User.deleted_at >= since,
            include_deleted=True,
            order_by=User.deleted_at.desc(),
            skip=skip,
            limit=limit,
        )


class UserProfileRepository(BaseRepository[UserProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserProfile)

    async def find_by_user(self, user_id: uuid.UUID) -> UserProfile | None:
        return await self.find_one(UserProfile.user_id == user_id)

    async def upsert_for_user(
        self,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> UserProfile:
        profile = await self.find_by_user(user_id)
        if profile is None:
            data["user_id"] = user_id
            return await self.create_from_dict(data)
        return await self.update(profile, data)


class UserAddressRepository(BaseRepository[UserAddress]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserAddress)

    async def find_by_user(self, user_id: uuid.UUID) -> list[UserAddress]:
        return await self.find_many(UserAddress.user_id == user_id)

    async def find_default(self, user_id: uuid.UUID) -> UserAddress | None:
        return await self.find_one(
            UserAddress.user_id == user_id,
            UserAddress.is_default == True,  # noqa: E712
        )

    async def clear_defaults(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(UserAddress)
            .where(UserAddress.user_id == user_id)
            .where(UserAddress.is_default == True)  # noqa: E712
            .values(is_default=False)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


class UserDeviceRepository(BaseRepository[UserDevice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserDevice)

    async def find_by_user(self, user_id: uuid.UUID) -> list[UserDevice]:
        return await self.find_many(UserDevice.user_id == user_id)

    async def find_by_token(self, push_token: str) -> UserDevice | None:
        return await self.find_one(UserDevice.push_notification_token == push_token)

    async def find_by_device_id(
        self,
        user_id: uuid.UUID,
        device_id: str,
    ) -> UserDevice | None:
        return await self.find_one(
            UserDevice.user_id == user_id,
            UserDevice.device_id == device_id,
        )

    async def deactivate_old_tokens(
        self,
        user_id: uuid.UUID,
        exclude_device_id: str,
    ) -> int:
        stmt = (
            update(UserDevice)
            .where(UserDevice.user_id == user_id)
            .where(UserDevice.device_id != exclude_device_id)
            .where(UserDevice.push_notification_token.is_not(None))
            .values(push_notification_token=None)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount


class UserRepositoryAggregate:
    """Aggregates all user-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.profiles = UserProfileRepository(session)
        self.addresses = UserAddressRepository(session)
        self.devices = UserDeviceRepository(session)
