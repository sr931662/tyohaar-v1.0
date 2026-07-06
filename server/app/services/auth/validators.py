"""
Async validators for the auth service domain.

These functions perform database lookups and raise domain exceptions when
invariants are violated. They are called from service methods and accept a
live UnitOfWork so they participate in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.auth.otp import OTPRecord
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.session import UserSession
from app.models.enums import OTPPurpose, OTPStatus
from app.repositories.unit_of_work import UnitOfWork
from app.services.auth.constants import (
    OTP_RATE_LIMIT_MAX_REQUESTS,
    OTP_RATE_LIMIT_WINDOW_SECONDS,
    REFRESH_TOKEN_REUSE_GRACE_SECONDS,
)
from app.services.auth.exceptions import (
    InvalidRefreshTokenError,
    OTPAttemptsExhaustedError,
    OTPExpiredError,
    OTPInvalidError,
    SessionExpiredError,
    TokenRevokedError,
)
from app.services.auth.helpers import verify_otp_hash
from app.services.exceptions import RateLimitError


async def validate_otp_rate_limit(
    identifier: str,
    uow: UnitOfWork,
) -> None:
    """
    Enforce per-identifier OTP send-rate limiting.

    Counts the number of OTPRecord rows for *identifier* created within the
    last OTP_RATE_LIMIT_WINDOW_SECONDS seconds. Raises RateLimitError when
    the limit is exceeded.
    """
    from datetime import timedelta
    from sqlalchemy import select, func

    assert uow.session is not None
    window_start = datetime.now(tz=timezone.utc) - timedelta(
        seconds=OTP_RATE_LIMIT_WINDOW_SECONDS
    )
    stmt = (
        select(func.count())
        .select_from(OTPRecord)
        .where(OTPRecord.identifier == identifier)
        .where(OTPRecord.created_at >= window_start)
    )
    result = await uow.session.execute(stmt)
    count: int = result.scalar_one() or 0

    if count >= OTP_RATE_LIMIT_MAX_REQUESTS:
        raise RateLimitError(
            f"OTP rate limit exceeded for {identifier}. "
            "Please wait before requesting another OTP.",
            retry_after_seconds=OTP_RATE_LIMIT_WINDOW_SECONDS,
        )


async def validate_otp_for_verification(
    identifier: str,
    otp_code: str,
    purpose: OTPPurpose,
    uow: UnitOfWork,
    secret_key: str,
) -> OTPRecord:
    """
    Find the active PENDING OTP for *identifier*+*purpose*, verify its hash,
    and return the OTPRecord on success.

    On each wrong attempt the attempt_count is incremented and persisted.
    Raises:
        OTPExpiredError:           OTP exists but has passed its expires_at.
        OTPAttemptsExhaustedError: attempt_count has reached max_attempts.
        OTPInvalidError:           Hash mismatch (wrong code).
    """
    otp_record = await uow.auth.otps.find_pending(identifier, purpose)

    if otp_record is None:
        raise OTPInvalidError("No active OTP found for this identifier and purpose.")

    if otp_record.is_expired:
        otp_record.status = OTPStatus.EXPIRED
        await uow.session.flush()  # type: ignore[union-attr]
        raise OTPExpiredError("OTP has expired. Please request a new one.")

    if otp_record.is_attempts_exhausted:
        raise OTPAttemptsExhaustedError(
            "Maximum verification attempts reached. Please request a new OTP."
        )

    if not verify_otp_hash(identifier, otp_code, otp_record.otp_hash, secret_key):
        otp_record.attempt_count += 1
        if otp_record.attempt_count >= otp_record.max_attempts:
            otp_record.status = OTPStatus.EXHAUSTED
        await uow.session.flush()  # type: ignore[union-attr]
        if otp_record.status == OTPStatus.EXHAUSTED:
            raise OTPAttemptsExhaustedError(
                "Maximum verification attempts reached. Please request a new OTP."
            )
        raise OTPInvalidError("Incorrect OTP. Please try again.")

    # Mark as verified
    otp_record.status = OTPStatus.VERIFIED
    otp_record.verified_at = datetime.now(tz=timezone.utc)
    await uow.session.flush()  # type: ignore[union-attr]
    return otp_record


async def validate_session(
    session_id: uuid.UUID,
    uow: UnitOfWork,
) -> UserSession:
    """
    Fetch and validate a UserSession by its primary key.

    Raises:
        SessionExpiredError: if session is not found, revoked, inactive, or expired.
    """
    session = await uow.auth.sessions.get_by_id(session_id)
    if session is None or not session.is_valid:
        raise SessionExpiredError(
            "Session not found or has expired. Please log in again."
        )
    return session


async def validate_refresh_token(
    raw_token: str,
    uow: UnitOfWork,
) -> RefreshToken:
    """
    Hash the raw token and look up the corresponding RefreshToken record.

    Raises:
        InvalidRefreshTokenError: if not found, revoked, used, or expired.
        TokenRevokedError:        if the token or its family has been revoked.
    """
    from app.services.auth.helpers import hash_token

    token_hash = hash_token(raw_token)
    record = await uow.auth.refresh_tokens.find_one(
        RefreshToken.token_hash == token_hash
    )

    if record is None:
        raise InvalidRefreshTokenError("Refresh token not found.")

    if record.is_revoked:
        raise TokenRevokedError("This refresh token has been revoked.")

    if record.is_used:
        # A short grace window absorbs the extremely common case of the same
        # user having the app open in two tabs: both tabs share one refresh
        # token via localStorage, and if both are near-expiry at once, both
        # can fire a refresh within milliseconds of each other. The first
        # wins and rotates the token; the second arrives here presenting the
        # now-used token. That is NOT an attack — treat it as a harmless
        # race and let the caller retry with whatever is currently in
        # storage, without nuking the legitimate session that just rotated.
        # Only reuse *outside* this window (a truly stale/stolen token) is
        # treated as an actual security incident.
        if record.used_at is not None:
            age = (datetime.now(tz=timezone.utc) - record.used_at).total_seconds()
            if age <= REFRESH_TOKEN_REUSE_GRACE_SECONDS:
                raise InvalidRefreshTokenError(
                    "Refresh token already used. Retry with the latest token."
                )

        # Reuse detected outside the grace window — revoke entire token family
        from app.models.enums import TokenRevocationReason
        await uow.auth.refresh_tokens.revoke_family(
            record.family_id,
            TokenRevocationReason.REUSE_DETECTED,
        )
        await uow.auth.sessions.revoke_session(
            await uow.auth.sessions.get_by_id(record.session_id),  # type: ignore[arg-type]
            TokenRevocationReason.REUSE_DETECTED,
        )
        raise TokenRevokedError(
            "Refresh token reuse detected. All sessions have been revoked for security."
        )

    if record.is_expired:
        raise InvalidRefreshTokenError("Refresh token has expired.")

    return record
