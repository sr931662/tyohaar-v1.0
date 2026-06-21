"""
Auth repository — OTP, session, and refresh token persistence.

Three sub-repositories are exposed through the AuthRepository aggregator.
Each handles one auth model; all share the same AsyncSession so they
participate in one transaction per UnitOfWork.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.otp import OTPRecord
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.session import UserSession
from app.models.enums import OTPPurpose, OTPStatus, SessionStatus, TokenRevocationReason
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    pass


# ── OTP ───────────────────────────────────────────────────────────────────────


class OTPRepository(BaseRepository[OTPRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OTPRecord)

    async def find_pending(
        self,
        identifier: str,
        purpose: OTPPurpose,
    ) -> OTPRecord | None:
        """Return the single PENDING OTP for identifier+purpose, or None."""
        return await self.find_one(
            OTPRecord.identifier == identifier,
            OTPRecord.purpose == purpose,
            OTPRecord.status == OTPStatus.PENDING,
        )

    async def supersede_all_pending(
        self,
        identifier: str,
        purpose: OTPPurpose,
    ) -> int:
        """Mark all PENDING OTPs for identifier+purpose as SUPERSEDED. Returns count."""
        stmt = (
            update(OTPRecord)
            .where(OTPRecord.identifier == identifier)
            .where(OTPRecord.purpose == purpose)
            .where(OTPRecord.status == OTPStatus.PENDING)
            .values(status=OTPStatus.SUPERSEDED)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def find_by_user(self, user_id: uuid.UUID) -> list[OTPRecord]:
        return await self.find_many(OTPRecord.user_id == user_id)

    async def find_expired(self) -> list[OTPRecord]:
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            OTPRecord.expires_at < now,
            OTPRecord.status == OTPStatus.PENDING,
        )

    async def delete_stale(self, before: datetime) -> int:
        """Hard-delete non-PENDING OTPs created before the given timestamp."""
        from sqlalchemy import delete as sa_delete
        stmt = (
            sa_delete(OTPRecord)
            .where(OTPRecord.created_at < before)
            .where(OTPRecord.status != OTPStatus.PENDING)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ── Session ───────────────────────────────────────────────────────────────────


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSession)

    async def find_by_token(self, token: str) -> UserSession | None:
        return await self.find_one(UserSession.session_token == token)

    async def find_active_for_user(self, user_id: uuid.UUID) -> list[UserSession]:
        return await self.find_many(
            UserSession.user_id == user_id,
            UserSession.is_active == True,  # noqa: E712
            UserSession.is_revoked == False,  # noqa: E712
        )

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        reason: TokenRevocationReason,
    ) -> int:
        """Revoke all active sessions for a user. Returns count of revoked rows."""
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_revoked == False)  # noqa: E712
            .values(
                is_active=False,
                is_revoked=True,
                revoked_at=now,
                revocation_reason=reason,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def revoke_session(
        self,
        instance: UserSession,
        reason: TokenRevocationReason,
    ) -> None:
        """Revoke a specific session in place (does not flush; caller must commit)."""
        instance.is_active = False
        instance.is_revoked = True
        instance.revoked_at = datetime.now(tz=timezone.utc)
        instance.revocation_reason = reason
        await self._session.flush()

    async def find_expired(self) -> list[UserSession]:
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            UserSession.expires_at < now,
            UserSession.is_active == True,  # noqa: E712
        )

    async def find_by_access_jti(self, jti: str) -> UserSession | None:
        return await self.find_one(UserSession.access_jti == jti)

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        return await self.count(
            UserSession.user_id == user_id,
            UserSession.is_active == True,  # noqa: E712
            UserSession.is_revoked == False,  # noqa: E712
        )


# ── Refresh Token ─────────────────────────────────────────────────────────────


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def find_by_jti(self, jti: str) -> RefreshToken | None:
        return await self.find_one(RefreshToken.jti == jti)

    async def find_family(self, family_id: uuid.UUID) -> list[RefreshToken]:
        return await self.find_many(RefreshToken.family_id == family_id)

    async def find_active_for_session(self, session_id: uuid.UUID) -> list[RefreshToken]:
        return await self.find_many(
            RefreshToken.session_id == session_id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )

    async def revoke_family(
        self,
        family_id: uuid.UUID,
        reason: TokenRevocationReason,
    ) -> int:
        """Revoke all tokens sharing family_id. Returns count of revoked rows."""
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .where(RefreshToken.is_revoked == False)  # noqa: E712
            .values(is_revoked=True, revoked_at=now, revocation_reason=reason)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def revoke_for_session(
        self,
        session_id: uuid.UUID,
        reason: TokenRevocationReason,
    ) -> int:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.session_id == session_id)
            .where(RefreshToken.is_revoked == False)  # noqa: E712
            .values(is_revoked=True, revoked_at=now, revocation_reason=reason)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def find_expired(self) -> list[RefreshToken]:
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            RefreshToken.expires_at < now,
            RefreshToken.is_revoked == False,  # noqa: E712
        )


# ── Aggregator ────────────────────────────────────────────────────────────────


class AuthRepository:
    """Namespace that groups all auth sub-repositories under one handle."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.otps = OTPRepository(session)
        self.sessions = SessionRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
