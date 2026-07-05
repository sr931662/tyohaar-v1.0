from __future__ import annotations

from app.services.exceptions import (
    AccountLockedError,
    AuthenticationError,
)


class OTPExpiredError(AuthenticationError):
    default_message = "OTP has expired. Please request a new one."


class OTPInvalidError(AuthenticationError):
    default_message = "Invalid OTP. Please check and try again."


class OTPAttemptsExhaustedError(AccountLockedError):
    default_message = "Maximum OTP attempts exceeded. Please request a new OTP."


class SessionExpiredError(AuthenticationError):
    default_message = "Session has expired. Please log in again."


class InvalidRefreshTokenError(AuthenticationError):
    default_message = "Refresh token is invalid or not found."


class TokenRevokedError(AuthenticationError):
    default_message = "Token has been revoked."


class InvalidCredentialsError(AuthenticationError):
    default_message = "Invalid email or password."


class WorkspaceAccessDeniedError(AuthenticationError):
    default_message = (
        "This portal is for Tyohaar vendors and staff. "
        "Customers should use the Tyohaar app."
    )
