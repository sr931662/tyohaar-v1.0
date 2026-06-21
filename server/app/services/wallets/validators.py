"""
Wallets domain validators — stateful checks that require the UoW/DB.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.models.wallets.wallet import Wallet, WalletStatus
from app.models.wallets.reward import UserReward, UserRewardStatus
from app.repositories.unit_of_work import UnitOfWork
from app.services.exceptions import InsufficientBalanceError, ValidationError
from app.services.wallets.constants import MAX_WALLET_CREDIT, MIN_WALLET_CREDIT
from app.services.wallets.exceptions import (
    RewardAlreadyRedeemedError,
    RewardExpiredError,
    RewardNotFoundError,
    WalletClosedError,
    WalletFrozenError,
    WalletNotFoundError,
    WalletOwnershipError,
    WalletSuspendedError,
)
from app.services.wallets.helpers import is_reward_expired


async def validate_wallet_active(wallet_id: uuid.UUID, uow: UnitOfWork) -> Wallet:
    """
    Fetch the wallet and ensure it is in ACTIVE status.

    Raises the appropriate domain exception for FROZEN, SUSPENDED, or CLOSED.
    """
    wallet = await uow.wallets.wallets.get_by_id(wallet_id)
    if wallet is None:
        raise WalletNotFoundError(str(wallet_id))

    if wallet.wallet_status == WalletStatus.FROZEN:
        raise WalletFrozenError()
    if wallet.wallet_status == WalletStatus.SUSPENDED:
        raise WalletSuspendedError()
    if wallet.wallet_status == WalletStatus.CLOSED:
        raise WalletClosedError()

    return wallet


def validate_sufficient_balance(wallet: Wallet, amount: Decimal) -> None:
    """Raise InsufficientBalanceError if available_balance < amount."""
    if wallet.available_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient wallet balance. "
            f"Available: ₹{wallet.available_balance}, required: ₹{amount}."
        )


async def validate_wallet_owned_by_user(
    wallet_id: uuid.UUID,
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> Wallet:
    """Fetch the wallet and verify it belongs to user_id."""
    wallet = await uow.wallets.wallets.get_by_id(wallet_id)
    if wallet is None:
        raise WalletNotFoundError(str(wallet_id))
    if wallet.user_id != user_id:
        raise WalletOwnershipError()
    return wallet


def validate_credit_amount(amount: Decimal) -> None:
    """Raise ValidationError if credit amount is outside the allowed per-transaction range."""
    if amount < MIN_WALLET_CREDIT:
        raise ValidationError(
            f"Credit amount must be at least ₹{MIN_WALLET_CREDIT}.",
            field="amount",
        )
    if amount > MAX_WALLET_CREDIT:
        raise ValidationError(
            f"Credit amount cannot exceed ₹{MAX_WALLET_CREDIT} per transaction.",
            field="amount",
        )


async def validate_reward_redeemable(
    reward_id: uuid.UUID,
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> UserReward:
    """
    Fetch the reward and verify it is redeemable by user_id.

    Checks:
    - Reward exists.
    - Belongs to user_id.
    - Status is ACTIVE.
    - Not expired.
    """
    reward = await uow.wallets.rewards.get_by_id(reward_id)
    if reward is None:
        raise RewardNotFoundError(str(reward_id))
    if reward.user_id != user_id:
        raise WalletOwnershipError("Reward does not belong to this user.")
    if reward.reward_status == UserRewardStatus.USED:
        raise RewardAlreadyRedeemedError()
    if reward.reward_status not in (UserRewardStatus.ACTIVE, UserRewardStatus.PENDING):
        raise RewardAlreadyRedeemedError(
            f"Reward is in non-redeemable status: {reward.reward_status}."
        )
    if is_reward_expired(reward.expires_at):
        raise RewardExpiredError()
    return reward
