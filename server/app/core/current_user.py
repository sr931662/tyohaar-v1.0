"""
FastAPI dependencies that resolve the authenticated user for a request.

Usage in route handlers
-----------------------
    from app.core.current_user import CurrentUserDep

    @router.get("/me")
    async def get_me(current_user: CurrentUserDep) -> UserResponse:
        return current_user

All dependencies here only perform authentication — they do not authorise.
Authorization (role / permission checks) is in core/permissions.py.
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from app.core.dependencies import get_user_service
from app.core.security import (
    extract_user_id_from_token,
    get_optional_token,
    get_token_from_header,
)
from app.models.enums import AccountStatus
from app.schemas.users.response import UserResponse
from app.services.exceptions import NotFoundError
from app.services.users.service import UserService


# ── Session check ─────────────────────────────────────────────────────────────
#
# Access tokens carry the id of the session they were issued for. Without this
# check a logged-out (or "log out of all devices") token kept working until it
# expired — up to 7 days. Active session ids are cached in-process for a
# minute, so this costs one lookup per session per minute rather than per
# request; a revoked session is refused within that minute (immediately on the
# instance that handled the logout, which calls forget_session).

_SESSION_TTL_SECONDS = 60.0
_SESSION_CACHE_MAX = 10_000
_active_sessions: dict[str, float] = {}


def forget_session(session_id: str) -> None:
    _active_sessions.pop(str(session_id), None)


def _session_id(token: str) -> str | None:
    from app.core.config import settings

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    sid = payload.get("session_id")
    return str(sid) if sid else None


async def _session_is_active(session_id: str) -> bool:
    from app.services.auth.service import AuthService

    now = time.monotonic()
    if _active_sessions.get(session_id, 0.0) > now:
        return True
    try:
        active = await AuthService().session_is_active(uuid.UUID(session_id))
    except ValueError:
        return False
    if active:
        if len(_active_sessions) >= _SESSION_CACHE_MAX:
            _active_sessions.clear()
        _active_sessions[session_id] = now + _SESSION_TTL_SECONDS
    return active


async def _assert_session_active(token: str) -> None:
    """401 if the token belongs to a session that has been ended."""
    session_id = _session_id(token)
    if session_id is None:
        return  # tokens without a session claim (internal/admin) are unaffected
    if not await _session_is_active(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has ended. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(get_token_from_header),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Dependency — resolves and returns the authenticated UserResponse.

    Steps:
      1. Validate the Bearer token and extract the user UUID.
      2. Load the user from the database via UserService.
      3. Reject suspended / deactivated / banned accounts with 403.

    Raises HTTP 401 for invalid/missing tokens or unknown users.
    Raises HTTP 403 for accounts that are not allowed to act.
    """
    user_id_str = extract_user_id_from_token(token)
    await _assert_session_active(token)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await user_service.get_user(user_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _assert_account_accessible(user)
    return user


async def get_optional_user(
    token: str | None = Depends(get_optional_token),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse | None:
    """
    Dependency — returns the authenticated user or None.

    Safe to use on public endpoints that optionally personalize their
    response when a valid token is present. Never raises on missing token.
    """
    if token is None:
        return None

    try:
        # extract_user_id_from_token raises HTTP 401 on an invalid or expired
        # token. On a public endpoint that must degrade to anonymous instead:
        # a client holding a stale token would otherwise be locked out of
        # pages that need no login at all.
        user_id_str = extract_user_id_from_token(token)
        await _assert_session_active(token)
        user_id = uuid.UUID(user_id_str)
        user = await user_service.get_user(user_id)
    except (ValueError, NotFoundError, HTTPException):
        return None

    if user.account_status not in (AccountStatus.ACTIVE, AccountStatus.PENDING_VERIFICATION):
        return None

    return user


def _assert_account_accessible(user: UserResponse) -> None:
    """Raise HTTP 403 if the account cannot act (suspended / deactivated / banned)."""
    blocked = {AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED, AccountStatus.BANNED}
    if user.account_status in blocked:
        detail_map = {
            AccountStatus.SUSPENDED: "Account is temporarily suspended.",
            AccountStatus.DEACTIVATED: "Account has been deactivated.",
            AccountStatus.BANNED: "Account has been permanently banned.",
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_map[user.account_status],
        )


# ── Typed aliases ─────────────────────────────────────────────────────────────

CurrentUserDep = Annotated[UserResponse, Depends(get_current_user)]
OptionalUserDep = Annotated[UserResponse | None, Depends(get_optional_user)]
