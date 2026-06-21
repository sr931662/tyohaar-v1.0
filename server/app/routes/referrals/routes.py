"""
Referrals Routes — referral codes, applications, rewards, and stats.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.referrals import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.referrals.response import (
    ReferralResponse,
    ReferralRewardResponse,
    ReferralStatsResponse,
)
from app.services.referrals.service import ReferralCodeResponse

router = APIRouter(prefix="/referrals", tags=["Referrals"])

# ── Referral code ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/code",
    ctrl.get_referral_code,
    methods=["GET"],
    response_model=SuccessResponse[ReferralCodeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Referral Code",
    description="Return the referral code assigned to the authenticated user.",
    operation_id="referrals_get_referral_code",
)

# ── Apply referral ────────────────────────────────────────────────────────────

router.add_api_route(
    "/apply",
    ctrl.apply_referral_code,
    methods=["POST"],
    response_model=SuccessResponse[ReferralResponse],
    status_code=status.HTTP_200_OK,
    summary="Apply Referral Code",
    description="Apply a referral code during onboarding to link referrer and referee.",
    operation_id="referrals_apply_referral_code",
)

# ── Stats (static, must precede /rewards paths) ───────────────────────────────

router.add_api_route(
    "/stats",
    ctrl.get_referral_stats,
    methods=["GET"],
    response_model=SuccessResponse[ReferralStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Referral Stats",
    description="Return aggregated referral statistics for the authenticated user.",
    operation_id="referrals_get_referral_stats",
)

# ── Rewards ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/rewards",
    ctrl.list_rewards,
    methods=["GET"],
    response_model=CursorPaginatedResponse[ReferralRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="List Referral Rewards",
    description="Return a cursor-paginated list of referral rewards for the authenticated user.",
    operation_id="referrals_list_rewards",
)

router.add_api_route(
    "/rewards/{reward_id}",
    ctrl.get_reward,
    methods=["GET"],
    response_model=SuccessResponse[ReferralRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Referral Reward",
    description="Return a single referral reward by ID. User ownership required.",
    operation_id="referrals_get_reward",
)

router.add_api_route(
    "/rewards/{reward_id}/activate",
    ctrl.activate_referral_reward,
    methods=["POST"],
    response_model=SuccessResponse[ReferralRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="Activate Referral Reward (Admin)",
    description="Activate a referral reward so it becomes redeemable. Admin access required.",
    operation_id="referrals_activate_referral_reward",
)

# ── Referral list ─────────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.list_referrals,
    methods=["GET"],
    response_model=CursorPaginatedResponse[ReferralResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Referrals",
    description="Return a cursor-paginated list of users referred by the authenticated user.",
    operation_id="referrals_list_referrals",
)

# ── Admin — trigger rewards ───────────────────────────────────────────────────

router.add_api_route(
    "/{referral_id}/rewards/trigger",
    ctrl.trigger_referral_rewards,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Trigger Referral Rewards (Admin)",
    description="Manually trigger reward distribution for a referral record. Admin access required.",
    operation_id="referrals_trigger_referral_rewards",
)
