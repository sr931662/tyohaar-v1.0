"""
DeletionService — the account deletion lifecycle.

    request()   → verified request recorded, account deactivated same instant
    cancel()    → user changed their mind, inside the recovery window
    status()    → what the user sees while they wait
    run_due()   → the daily job: purge everything past its recovery window

Deliberate non-features:

  * There is no inactivity trigger anywhere in this module. Tyohaar users
    routinely disappear for a year or more between celebrations, and a dormant
    account is not a deletion request.

  * There is no unauthenticated deletion path. A request is only accepted from
    a session that already proved who it belongs to, which is why `verified_at`
    equals `requested_at` for every request this service creates.

  * Vendor and admin accounts are refused. They carry settlement and audit
    obligations that the consumer pipeline does not model, and quietly running
    a consumer purge over one would be worse than refusing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.retention import PURGE_DEADLINE, RECOVERY_WINDOW
from app.models.enums import (
    AccountStatus,
    DeletionRequestChannel,
    DeletionRequestStatus,
    UserRole,
)
from app.models.users.deletion_request import DeletionRequest
from app.models.users.user import User
from app.services.base import BaseService
from app.services.deletion.handlers.session_access import purge_session_access
from app.services.deletion.runner import run_purge
from app.services.exceptions import ConflictError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

#: Roles the consumer deletion flow will not act on.
_EXCLUDED_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.VENDOR}

_LIVE_STATUSES = (
    DeletionRequestStatus.PENDING_VERIFICATION,
    DeletionRequestStatus.RECOVERABLE,
    DeletionRequestStatus.PURGING,
)


def hash_identifier(raw: str) -> str:
    """Keyed HMAC of a phone or email, for the compliance record.

    Keyed rather than a plain digest: a bare SHA-256 of a 10-digit Indian
    mobile number is trivially reversible by enumeration, which would make the
    "no raw identifiers retained" property worthless.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        raw.strip().lower().encode(),
        hashlib.sha256,
    ).hexdigest()


class DeletionService(BaseService):
    """Account deletion lifecycle."""

    # ── Request ───────────────────────────────────────────────────────────────

    async def request_deletion(
        self,
        *,
        user_id: uuid.UUID,
        channel: DeletionRequestChannel = DeletionRequestChannel.IN_APP,
    ) -> DeletionRequest:
        """Record a verified deletion request and deactivate the account now.

        The caller is already authenticated, so the bearer token *is* the
        identity proof — there is no second verification step to wait on, and
        adding one would only delay the point at which access stops.
        """
        now = datetime.now(tz=timezone.utc)

        async with self._uow() as uow:
            session = uow.session
            user = await session.get(User, user_id)
            if user is None:
                raise NotFoundError("User", str(user_id))

            if user.role in _EXCLUDED_ROLES:
                raise ValidationError(
                    "Vendor and administrator accounts cannot be closed through "
                    "the customer deletion flow. Please contact support so the "
                    "correct offboarding process can be followed."
                )

            existing = (
                await session.execute(
                    select(DeletionRequest).where(
                        DeletionRequest.user_id == user_id,
                        DeletionRequest.status.in_(_LIVE_STATUSES),
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise ConflictError(
                    "A deletion request is already in progress for this account."
                )

            request = DeletionRequest(
                id=uuid.uuid4(),
                user_id=user_id,
                identifier_hash=hash_identifier(user.phone or user.email or str(user_id)),
                channel=channel,
                status=DeletionRequestStatus.RECOVERABLE,
                requested_at=now,
                verified_at=now,
                recovery_ends_at=now + RECOVERY_WINDOW,
                purge_due_at=now + PURGE_DEADLINE,
            )
            session.add(request)

            # Day 0: the account stops working immediately. Nothing is
            # destroyed — that is what the recovery window is for — but the
            # user is signed out, invisible and unreachable by notification.
            user.account_status = AccountStatus.DEACTIVATED

            await purge_session_access(session, user_id)

            await session.flush()
            await session.refresh(request)
            return request

    # ── Recovery ──────────────────────────────────────────────────────────────

    async def cancel_deletion(self, *, user_id: uuid.UUID) -> DeletionRequest:
        """Restore an account inside the recovery window.

        Only RECOVERABLE requests can be cancelled. Once the purge has started
        there is nothing left to restore, and pretending otherwise would be a
        worse experience than saying so.
        """
        now = datetime.now(tz=timezone.utc)

        async with self._uow() as uow:
            session = uow.session
            request = (
                await session.execute(
                    select(DeletionRequest).where(
                        DeletionRequest.user_id == user_id,
                        DeletionRequest.status == DeletionRequestStatus.RECOVERABLE,
                    )
                )
            ).scalar_one_or_none()

            if request is None:
                raise NotFoundError("Restorable deletion request")
            if request.recovery_ends_at and request.recovery_ends_at <= now:
                raise ValidationError(
                    "The recovery window for this request has closed."
                )

            request.status = DeletionRequestStatus.CANCELLED
            request.cancelled_at = now

            user = await session.get(User, user_id)
            if user is not None:
                user.account_status = AccountStatus.ACTIVE
                user.deleted_at = None

            await session.flush()
            await session.refresh(request)
            return request

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_active_request(
        self, *, user_id: uuid.UUID
    ) -> DeletionRequest | None:
        async with self._uow() as uow:
            return (
                await uow.session.execute(
                    select(DeletionRequest)
                    .where(DeletionRequest.user_id == user_id)
                    .order_by(DeletionRequest.requested_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

    # ── Purge ─────────────────────────────────────────────────────────────────

    async def find_due(self, *, now: datetime | None = None) -> list[uuid.UUID]:
        """Request ids whose recovery window has closed and are not on hold."""
        now = now or datetime.now(tz=timezone.utc)

        async with self._uow() as uow:
            rows = await uow.session.execute(
                select(DeletionRequest.id).where(
                    DeletionRequest.status.in_(
                        (
                            DeletionRequestStatus.RECOVERABLE,
                            DeletionRequestStatus.PURGING,
                            DeletionRequestStatus.INCOMPLETE,
                        )
                    ),
                    DeletionRequest.recovery_ends_at <= now,
                    # A legal hold suspends the purge. An unconditional purge
                    # could destroy records we are obliged to produce.
                    (
                        DeletionRequest.legal_hold_until.is_(None)
                        | (DeletionRequest.legal_hold_until <= now)
                    ),
                )
            )
            return list(rows.scalars().all())

    async def purge_request(self, *, request_id: uuid.UUID) -> DeletionRequest:
        """Run the purge for one request and record the outcome.

        Idempotent at this level too: re-running a PURGED request re-executes
        the handlers (they find nothing) and rewrites the same terminal state.
        """
        now = datetime.now(tz=timezone.utc)

        # Mark PURGING in its own transaction so a crash mid-run is visible
        # rather than looking like a request that was never picked up.
        async with self._uow() as uow:
            request = await uow.session.get(DeletionRequest, request_id)
            if request is None:
                raise NotFoundError("Deletion request", str(request_id))
            if request.status == DeletionRequestStatus.CANCELLED:
                raise ValidationError("This deletion request was cancelled.")
            if request.user_id is None:
                # Already fully purged: the user reference was cleared on
                # completion. Nothing to do.
                return request

            user_id = request.user_id
            request.status = DeletionRequestStatus.PURGING
            request.attempt_count += 1

        result = await run_purge(user_id, session_factory=self._session_factory)

        async with self._uow() as uow:
            request = await uow.session.get(DeletionRequest, request_id)
            if request is None:  # pragma: no cover - defensive
                raise NotFoundError("Deletion request", str(request_id))

            request.purge_report = result.as_dict()
            request.completed_at = now

            if result.ok:
                request.status = DeletionRequestStatus.PURGED
                # Sever the last live link to the person. From here the record
                # proves a deletion happened without naming who it was.
                request.user_id = None
            else:
                request.status = DeletionRequestStatus.INCOMPLETE
                logger.warning(
                    "purge incomplete",
                    extra={
                        "request_id": str(request_id),
                        "errors": result.errors,
                    },
                )

            await uow.session.flush()
            await uow.session.refresh(request)
            return request

    async def run_due(self, *, now: datetime | None = None) -> dict:
        """Purge every due request. Entry point for the daily job."""
        due = await self.find_due(now=now)
        purged, incomplete, failed = 0, 0, 0

        for request_id in due:
            try:
                request = await self.purge_request(request_id=request_id)
            except Exception:  # noqa: BLE001 - one bad request must not stop the batch
                logger.exception(
                    "purge request raised", extra={"request_id": str(request_id)}
                )
                failed += 1
                continue

            if request.status == DeletionRequestStatus.PURGED:
                purged += 1
            else:
                incomplete += 1

        return {
            "due": len(due),
            "purged": purged,
            "incomplete": incomplete,
            "failed": failed,
        }
