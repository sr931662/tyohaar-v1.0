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

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

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

    user_id_str = extract_user_id_from_token(token)

    try:
        user_id = uuid.UUID(user_id_str)
        user = await user_service.get_user(user_id)
    except (ValueError, NotFoundError):
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
