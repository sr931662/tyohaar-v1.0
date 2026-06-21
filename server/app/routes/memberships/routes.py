"""
Memberships Routes — plans, subscriptions, renewals, and feature access.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.memberships import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.memberships.response import (
    MembershipPlanResponse,
    MembershipResponse,
)

router = APIRouter(prefix="/memberships", tags=["Memberships"])

# ── Plans (static — must precede /{membership_id}) ───────────────────────────

router.add_api_route(
    "/plans",
    ctrl.list_plans,
    methods=["GET"],
    response_model=SuccessResponse[list[MembershipPlanResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Membership Plans",
    description="Return all active membership plans. Public endpoint.",
    operation_id="memberships_list_plans",
)

router.add_api_route(
    "/plans",
    ctrl.create_plan,
    methods=["POST"],
    response_model=SuccessResponse[MembershipPlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Membership Plan (Admin)",
    description="Create a new membership plan. Admin access required.",
    operation_id="memberships_create_plan",
)

router.add_api_route(
    "/plans/{plan_id}",
    ctrl.get_plan,
    methods=["GET"],
    response_model=SuccessResponse[MembershipPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Membership Plan",
    description="Return a single membership plan by ID. Public endpoint.",
    operation_id="memberships_get_plan",
)

router.add_api_route(
    "/plans/{plan_id}",
    ctrl.update_plan,
    methods=["PUT"],
    response_model=SuccessResponse[MembershipPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Membership Plan (Admin)",
    description="Update an existing membership plan. Admin access required.",
    operation_id="memberships_update_plan",
)

router.add_api_route(
    "/plans/{plan_id}",
    ctrl.deactivate_plan,
    methods=["DELETE"],
    response_model=SuccessResponse[MembershipPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Membership Plan (Admin)",
    description="Soft-deactivate a membership plan so new subscribers cannot join. Admin access required.",
    operation_id="memberships_deactivate_plan",
)

# ── Feature access check (static — must precede /{membership_id}) ────────────

router.add_api_route(
    "/features/{feature}/access",
    ctrl.check_membership_feature_access,
    methods=["GET"],
    response_model=SuccessResponse[bool],
    status_code=status.HTTP_200_OK,
    summary="Check Feature Access",
    description="Check whether the authenticated user's active membership grants access to the specified feature.",
    operation_id="memberships_check_feature_access",
)

# ── Subscribe / Active membership ─────────────────────────────────────────────

router.add_api_route(
    "/subscribe",
    ctrl.subscribe,
    methods=["POST"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to Membership",
    description="Subscribe the authenticated user to the specified membership plan.",
    operation_id="memberships_subscribe",
)

router.add_api_route(
    "/active",
    ctrl.get_active_membership,
    methods=["GET"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Active Membership",
    description="Return the currently active membership for the authenticated user.",
    operation_id="memberships_get_active_membership",
)

# ── Admin — all memberships ───────────────────────────────────────────────────

router.add_api_route(
    "/admin/all",
    ctrl.list_all_memberships,
    methods=["GET"],
    response_model=CursorPaginatedResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Memberships (Admin)",
    description="Return all memberships across all users. Admin access required.",
    operation_id="memberships_list_all_memberships",
)

router.add_api_route(
    "/admin/{membership_id}/expire",
    ctrl.force_expire_membership,
    methods=["POST"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="Force Expire Membership (Admin)",
    description="Immediately expire a membership. Admin access required.",
    operation_id="memberships_force_expire_membership",
)

# ── Per-membership operations ─────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.list_user_memberships,
    methods=["GET"],
    response_model=CursorPaginatedResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Memberships",
    description="Return the membership history for the authenticated user.",
    operation_id="memberships_list_user_memberships",
)

router.add_api_route(
    "/{membership_id}",
    ctrl.get_membership,
    methods=["GET"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Membership",
    description="Return a single membership record by ID. User ownership required.",
    operation_id="memberships_get_membership",
)

router.add_api_route(
    "/{membership_id}/cancel",
    ctrl.cancel_membership,
    methods=["POST"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel Membership",
    description="Cancel the specified membership. User ownership required.",
    operation_id="memberships_cancel_membership",
)

router.add_api_route(
    "/{membership_id}/renew",
    ctrl.renew_membership,
    methods=["POST"],
    response_model=SuccessResponse[MembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="Renew Membership",
    description="Renew the specified membership for another billing cycle. User ownership required.",
    operation_id="memberships_renew_membership",
)
