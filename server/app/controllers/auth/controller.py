"""
Auth Controller — OTP authentication, token rotation, session management.
"""

from __future__ import annotations

import logging
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
from app.models.enums import OTPDeliveryChannel, OTPPurpose
from app.schemas.auth.create import (
    EmailVerifyOTPCreate,
    GoogleAuthCreate,
    OTPRequestCreate,
    OTPVerifyCreate,
    PasswordResetConfirmCreate,
    UserRegisterCreate,
    UserLoginCreate,
    VendorRegisterCreate,
)
from app.schemas.auth.response import OTPSentResponse, SessionResponse
from app.services.auth.service import RegisterResponse, TokenPairResponse
from app.services.admin.helpers import verify_admin_password

logger = logging.getLogger(__name__)


class _RefreshRequest(BaseModel):
    refresh_token: str


class _VendorLoginRequest(BaseModel):
    email: str
    password: str


class _WorkspaceLoginRequest(BaseModel):
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
    request: Request,
) -> SuccessResponse[dict]:
    result = await service.authenticate_user(
        email=body.email,
        password=body.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return SuccessResponse(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
        },
        message="Vendor login successful.",
    )


async def workspace_login(
    body: _WorkspaceLoginRequest,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[dict]:
    result = await service.authenticate_workspace_user(
        email=body.email,
        password=body.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return SuccessResponse(data=result, message="Login successful.")


async def register_vendor(
    body: VendorRegisterCreate,
    service: AuthServiceDep,
) -> SuccessResponse[dict]:
    result = await service.register_vendor(body)
    return SuccessResponse(
        data=result,
        message="Vendor registration submitted. You can sign in once an admin approves your account.",
    )


async def reset_password(
    body: PasswordResetConfirmCreate,
    service: AuthServiceDep,
) -> SuccessResponse[None]:
    await service.reset_password(body)
    return SuccessResponse(data=None, message="Password reset successfully. You can now log in.")


async def google_vendor_auth(
    body: GoogleAuthCreate,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[dict]:
    result = await service.authenticate_vendor_google(
        id_token_str=body.id_token,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    message = (
        "Signed in successfully."
        if "access_token" in result
        else "Your vendor account is pending admin approval."
    )
    return SuccessResponse(data=result, message=message)


async def register(
    body: UserRegisterCreate,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[RegisterResponse]:
    result = await service.register_user(
        data=body,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    # Best-effort: the account is already created, so a transient email
    # failure must not fail registration itself — the client surfaces
    # email_verification_sent=False and lets the user retry from the
    # verification screen's Resend action.
    email_sent = True
    try:
        await service.send_otp(
            phone=body.email,
            channel=OTPDeliveryChannel.EMAIL,
            purpose=OTPPurpose.EMAIL_VERIFICATION,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    except Exception:
        logger.exception("Failed to send verification email during registration for %s", body.email)
        email_sent = False

    response_data = RegisterResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        session_id=result.session_id,
        user_id=result.user_id,
        email_verification_sent=email_sent,
    )
    message = (
        "Registration successful."
        if email_sent
        else "Registration successful, but we couldn't send the verification email."
    )
    return SuccessResponse(data=response_data, message=message)


async def verify_email_otp(
    body: EmailVerifyOTPCreate,
    service: AuthServiceDep,
) -> SuccessResponse[None]:
    await service.verify_email_otp(email=body.email, otp_code=body.otp_code)
    return SuccessResponse(data=None, message="Email verified successfully.")


async def login(
    body: UserLoginCreate,
    service: AuthServiceDep,
    request: Request,
) -> SuccessResponse[TokenPairResponse]:
    result = await service.authenticate_user(
        email=body.email,
        password=body.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return SuccessResponse(data=result, message="Login successful.")


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
