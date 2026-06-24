"""
Auth Controller — OTP authentication, token rotation, session management.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.current_user import CurrentUserDep
from app.core.dependencies import AuthServiceDep
from app.core.responses import SuccessResponse
from app.core.security import create_access_token, get_token_from_header
from app.schemas.auth.create import OTPRequestCreate, OTPVerifyCreate
from app.schemas.auth.response import OTPSentResponse, SessionResponse
from app.services.auth.service import TokenPairResponse
from app.services.admin.helpers import verify_admin_password


class _RefreshRequest(BaseModel):
    refresh_token: str


class _VendorLoginRequest(BaseModel):
    email: str
    password: str


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def vendor_login(
    body: _VendorLoginRequest,
    service: AuthServiceDep,
) -> SuccessResponse[dict]:
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.users.user import User
    from app.models.enums import UserRole, AccountStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

    if user is None or user.role != UserRole.VENDOR:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")
    stored_hash = getattr(user, "password_hash", None) or ""
    if not stored_hash or not verify_admin_password(body.password, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(str(user.id))
    return SuccessResponse(data={"access_token": token}, message="Vendor login successful.")


async def request_otp(
    body: OTPRequestCreate,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[OTPSentResponse]:
    result = await service.send_otp(
        phone=body.identifier,
        channel=body.channel,
        purpose=body.purpose,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        device_fingerprint=body.device_fingerprint,
    )
    return SuccessResponse(data=result, message="OTP sent successfully.")


async def verify_otp(
    body: OTPVerifyCreate,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[TokenPairResponse]:
    result = await service.verify_otp(
        data=body,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return SuccessResponse(data=result, message="OTP verified successfully.")


async def refresh_token(
    body: _RefreshRequest,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[TokenPairResponse]:
    result = await service.refresh_access_token(
        raw_refresh_token=body.refresh_token,
        ip_address=_client_ip(request),
    )
    return SuccessResponse(data=result, message="Token refreshed successfully.")


async def logout(
    token: Annotated[str, Depends(get_token_from_header)],
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> SuccessResponse[None]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        session_id_str: str | None = payload.get("session_id")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if session_id_str:
        try:
            await service.logout(session_id=uuid.UUID(session_id_str))
        except ValueError:
            pass
    return SuccessResponse(data=None, message="Logged out successfully.")


async def logout_all_devices(
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> SuccessResponse[None]:
    await service.logout_all_devices(user_id=current_user.id)
    return SuccessResponse(data=None, message="All sessions terminated.")


async def get_active_sessions(
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> SuccessResponse[list[SessionResponse]]:
    sessions = await service.get_active_sessions(user_id=current_user.id)
    return SuccessResponse(data=sessions, message="Active sessions retrieved.")
