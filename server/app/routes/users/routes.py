"""
Users Routes — user account, profile, addresses, and device management.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.users import controller as ctrl
from app.core.responses import SuccessResponse
from app.schemas.users.response import (
    UserAddressResponse,
    UserDeviceResponse,
    UserProfileResponse,
    UserResponse,
)
from app.services.users.service import UserFullResponse

router = APIRouter(prefix="/users", tags=["Users"])

# ── Current user ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/me",
    ctrl.get_me,
    methods=["GET"],
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Profile",
    description="Return the full profile of the currently authenticated user.",
    operation_id="users_get_me",
)

router.add_api_route(
    "/me",
    ctrl.update_me,
    methods=["PUT"],
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update My Profile",
    description="Update top-level fields on the authenticated user's account.",
    operation_id="users_update_me",
)

router.add_api_route(
    "/me",
    ctrl.delete_me,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Deactivate My Account",
    description="Soft-delete (deactivate) the authenticated user's account.",
    operation_id="users_delete_me",
)

# ── Addresses ─────────────────────────────────────────────────────────────────

router.add_api_route(
    "/me/addresses",
    ctrl.list_addresses,
    methods=["GET"],
    response_model=SuccessResponse[list[UserAddressResponse]],
    status_code=status.HTTP_200_OK,
    summary="List My Addresses",
    description="Return all saved delivery/event addresses for the authenticated user.",
    operation_id="users_list_addresses",
)

router.add_api_route(
    "/me/addresses",
    ctrl.add_address,
    methods=["POST"],
    response_model=SuccessResponse[UserAddressResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Address",
    description="Save a new address to the authenticated user's address book.",
    operation_id="users_add_address",
)

router.add_api_route(
    "/me/addresses/{address_id}",
    ctrl.get_address,
    methods=["GET"],
    response_model=SuccessResponse[UserAddressResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Address",
    description="Return a single address by ID belonging to the authenticated user.",
    operation_id="users_get_address",
)

router.add_api_route(
    "/me/addresses/{address_id}",
    ctrl.update_address,
    methods=["PUT"],
    response_model=SuccessResponse[UserAddressResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Address",
    description="Update fields on an existing address owned by the authenticated user.",
    operation_id="users_update_address",
)

router.add_api_route(
    "/me/addresses/{address_id}",
    ctrl.delete_address,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Address",
    description="Remove an address from the authenticated user's address book.",
    operation_id="users_delete_address",
)

# ── Devices ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/me/devices",
    ctrl.list_devices,
    methods=["GET"],
    response_model=SuccessResponse[list[UserDeviceResponse]],
    status_code=status.HTTP_200_OK,
    summary="List My Devices",
    description="Return all registered push-notification devices for the authenticated user.",
    operation_id="users_list_devices",
)

router.add_api_route(
    "/me/devices",
    ctrl.register_device,
    methods=["POST"],
    response_model=SuccessResponse[UserDeviceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Device",
    description="Register a new device (and its push token) for the authenticated user.",
    operation_id="users_register_device",
)

router.add_api_route(
    "/me/devices/{device_id}",
    ctrl.deactivate_device,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Device",
    description="Deactivate a device so it no longer receives push notifications.",
    operation_id="users_deactivate_device",
)

# ── Per-user profile (ownership-gated) ────────────────────────────────────────

router.add_api_route(
    "/{user_id}",
    ctrl.get_profile,
    methods=["GET"],
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Profile",
    description="Return a user profile by ID. Requires ownership or admin role.",
    operation_id="users_get_profile",
)

router.add_api_route(
    "/{user_id}/profile",
    ctrl.update_profile,
    methods=["PUT"],
    response_model=SuccessResponse[UserProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
    description="Update extended profile fields for a user. Requires ownership or admin role.",
    operation_id="users_update_profile",
)

# ── Admin ─────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{user_id}/full",
    ctrl.get_user_full,
    methods=["GET"],
    response_model=SuccessResponse[UserFullResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Full User (Admin)",
    description="Return the complete user record including internal fields. Admin access required.",
    operation_id="users_get_user_full",
)
