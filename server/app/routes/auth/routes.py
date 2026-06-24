"""
Auth Routes — OTP authentication, token rotation, session management.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.auth import controller as ctrl
from app.core.responses import SuccessResponse
from app.schemas.auth.response import OTPSentResponse, SessionResponse
from app.services.auth.service import TokenPairResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

router.add_api_route(
    "/vendor/login",
    ctrl.vendor_login,
    methods=["POST"],
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Vendor Login",
    description="Authenticate a vendor user with email and password. Returns a JWT access token.",
    operation_id="auth_vendor_login",
)

router.add_api_route(
    "/otp/request",
    ctrl.request_otp,
    methods=["POST"],
    response_model=SuccessResponse[OTPSentResponse],
    status_code=status.HTTP_200_OK,
    summary="Request OTP",
    description="Send a one-time password to the specified phone number via the chosen channel (SMS or WhatsApp).",
    operation_id="auth_request_otp",
)

router.add_api_route(
    "/otp/verify",
    ctrl.verify_otp,
    methods=["POST"],
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description="Verify the submitted OTP and return a JWT access/refresh token pair.",
    operation_id="auth_verify_otp",
)

router.add_api_route(
    "/token/refresh",
    ctrl.refresh_token,
    methods=["POST"],
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new access/refresh token pair.",
    operation_id="auth_refresh_token",
)

router.add_api_route(
    "/logout",
    ctrl.logout,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Invalidate the current session associated with the bearer token.",
    operation_id="auth_logout",
)

router.add_api_route(
    "/logout/all",
    ctrl.logout_all_devices,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Logout All Devices",
    description="Terminate all active sessions for the authenticated user across every device.",
    operation_id="auth_logout_all_devices",
)

router.add_api_route(
    "/sessions",
    ctrl.get_active_sessions,
    methods=["GET"],
    response_model=SuccessResponse[list[SessionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Active Sessions",
    description="Return all currently active sessions for the authenticated user.",
    operation_id="auth_list_active_sessions",
)
