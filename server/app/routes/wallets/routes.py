"""
Wallets Routes — wallet lifecycle, balance operations, transactions, and rewards.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.wallets import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.wallets.response import (
    UserRewardResponse,
    WalletResponse,
    WalletTransactionResponse,
)
from app.services.wallets.service import RewardBalanceResponse

router = APIRouter(prefix="/wallets", tags=["Wallets"])

# ── Wallet lifecycle ──────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.create_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Wallet",
    description="Provision a new wallet for the authenticated user.",
    operation_id="wallets_create_wallet",
)

router.add_api_route(
    "/me",
    ctrl.get_wallet,
    methods=["GET"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Wallet",
    description="Return the wallet belonging to the authenticated user.",
    operation_id="wallets_get_wallet",
)

router.add_api_route(
    "/{wallet_id}",
    ctrl.get_wallet_by_id,
    methods=["GET"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Wallet by ID",
    description="Return a wallet by its ID. User ownership required.",
    operation_id="wallets_get_wallet_by_id",
)

# ── Admin wallet operations ───────────────────────────────────────────────────

router.add_api_route(
    "/admin/credit/{user_id}",
    ctrl.credit_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Credit Wallet (Admin)",
    description="Credit the wallet of the specified user. Admin access required. Pass `amount`, `description`, and optional `reference_id`/`reference_type` as query parameters.",
    operation_id="wallets_credit_wallet",
)

router.add_api_route(
    "/admin/debit/{user_id}",
    ctrl.debit_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Debit Wallet (Admin)",
    description="Debit the wallet of the specified user. Admin access required. Pass `amount`, `description`, and optional `reference_id`/`reference_type` as query parameters.",
    operation_id="wallets_debit_wallet",
)

router.add_api_route(
    "/admin/rewards/{user_id}",
    ctrl.award_reward,
    methods=["POST"],
    response_model=SuccessResponse[UserRewardResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Award Reward (Admin)",
    description="Award a reward to the specified user. Admin access required.",
    operation_id="wallets_award_reward",
)

router.add_api_route(
    "/{wallet_id}/freeze",
    ctrl.freeze_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Freeze Wallet (Admin)",
    description="Freeze a wallet to block all transactions. Admin access required. Pass `reason` as a query parameter.",
    operation_id="wallets_freeze_wallet",
)

router.add_api_route(
    "/{wallet_id}/unfreeze",
    ctrl.unfreeze_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Unfreeze Wallet (Admin)",
    description="Restore a frozen wallet to active status. Admin access required.",
    operation_id="wallets_unfreeze_wallet",
)

router.add_api_route(
    "/{wallet_id}/close",
    ctrl.close_wallet,
    methods=["POST"],
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Close Wallet (Admin)",
    description="Permanently close a wallet. Admin access required.",
    operation_id="wallets_close_wallet",
)

# ── Transactions ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/me/transactions",
    ctrl.list_transactions,
    methods=["GET"],
    response_model=CursorPaginatedResponse[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Wallet Transactions",
    description="Return a cursor-paginated, filterable list of wallet transactions for the authenticated user.",
    operation_id="wallets_list_transactions",
)

router.add_api_route(
    "/me/transactions/{tx_id}",
    ctrl.get_transaction,
    methods=["GET"],
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Wallet Transaction",
    description="Return a single wallet transaction by ID. User ownership required.",
    operation_id="wallets_get_transaction",
)

# ── Rewards ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/me/rewards/balance",
    ctrl.get_reward_balance,
    methods=["GET"],
    response_model=SuccessResponse[RewardBalanceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Reward Balance",
    description="Return the total redeemable reward balance for the authenticated user.",
    operation_id="wallets_get_reward_balance",
)

router.add_api_route(
    "/me/rewards",
    ctrl.list_rewards,
    methods=["GET"],
    response_model=CursorPaginatedResponse[UserRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Rewards",
    description="Return a cursor-paginated list of rewards for the authenticated user.",
    operation_id="wallets_list_rewards",
)

router.add_api_route(
    "/rewards/{reward_id}/activate",
    ctrl.activate_reward,
    methods=["POST"],
    response_model=SuccessResponse[UserRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="Activate Reward (Admin)",
    description="Activate an awarded reward so it becomes redeemable. Admin access required.",
    operation_id="wallets_activate_reward",
)

router.add_api_route(
    "/rewards/{reward_id}/redeem",
    ctrl.redeem_reward,
    methods=["POST"],
    response_model=SuccessResponse[UserRewardResponse],
    status_code=status.HTTP_200_OK,
    summary="Redeem Reward",
    description="Redeem an active reward to credit the user's wallet.",
    operation_id="wallets_redeem_reward",
)
