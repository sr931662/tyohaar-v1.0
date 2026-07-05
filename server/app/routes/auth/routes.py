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
    "/register",
    ctrl.register,
    methods=["POST"],
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Create a new customer account using email and password.",
    operation_id="auth_register",
)

router.add_api_route(
    "/login",
    ctrl.login,
    methods=["POST"],
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate a customer using email and password.",
    operation_id="auth_login",
)

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
    "/workspace/login",
    ctrl.workspace_login,
    methods=["POST"],
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Workspace Login (Vendor + Admin/Staff)",
    description=(
        "Single login entry point for the vendor portal and admin panel. "
        "Authenticates by email/password and returns the user's role "
        "(vendor | admin | super_admin) alongside the token pair, so the "
        "frontend can route to the correct portal. Customer accounts are "
        "rejected outright."
    ),
    operation_id="auth_workspace_login",
)

router.add_api_route(
    "/vendor/register",
    ctrl.register_vendor,
    methods=["POST"],
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Vendor Registration",
    description="Register a new vendor account (pending admin approval) using email and password.",
    operation_id="auth_vendor_register",
)

router.add_api_route(
    "/password/reset",
    ctrl.reset_password,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Verify an emailed OTP (purpose=password_reset) and set a new password.",
    operation_id="auth_reset_password",
)

router.add_api_route(
    "/vendor/google",
    ctrl.google_vendor_auth,
    methods=["POST"],
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Vendor Google Sign-In",
    description="Authenticate or register a vendor using a Google ID token.",
    operation_id="auth_vendor_google",
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
