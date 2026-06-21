"""
WalletService — orchestrates all wallet domain business logic.

CRITICAL: All balance mutations (credit / debit) use SELECT FOR UPDATE via
uow.wallets.wallets.get_by_user_with_lock to prevent race conditions.

Side effects are executed AFTER the async with block exits.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import RewardType, WalletTransactionType, WalletType
from app.models.wallets.reward import UserRewardStatus
from app.models.wallets.wallet import WalletStatus
from app.schemas.base import CursorPage
from app.schemas.wallets.create import UserRewardCreate
from app.schemas.wallets.filters import WalletTransactionFilters
from app.schemas.wallets.response import (
    UserRewardResponse,
    WalletResponse,
    WalletTransactionResponse,
)
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError, InsufficientBalanceError
from app.services.wallets.constants import (
    MAX_WALLET_BALANCE,
    MIN_WALLET_DEBIT,
    REWARD_EXPIRY_DAYS,
)
from app.services.wallets.exceptions import (
    RewardAlreadyRedeemedError,
    RewardNotFoundError,
    WalletAlreadyExistsError,
    WalletBalanceLimitError,
    WalletClosedError,
    WalletFrozenError,
    WalletNotFoundError,
    WalletSuspendedError,
)
from app.services.wallets.helpers import calculate_reward_points_value, is_reward_expired
from app.services.wallets.validators import (
    validate_credit_amount,
    validate_reward_redeemable,
    validate_sufficient_balance,
    validate_wallet_active,
    validate_wallet_owned_by_user,
)

logger = logging.getLogger(__name__)


@dataclass
class RewardBalanceResponse:
    """Aggregated active reward balance for a user."""

    user_id: uuid.UUID
    total_active_value: Decimal
    active_reward_count: int


class WalletService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Wallet Lifecycle ──────────────────────────────────────────────────────

    async def create_wallet(self, user_id: uuid.UUID) -> WalletResponse:
        """
        Provision a new ACTIVE wallet for user_id.
        Raises WalletAlreadyExistsError if one already exists.
        """
        async with self._uow() as uow:
            existing = await uow.wallets.wallets.find_by_user(user_id)
            if existing is not None:
                raise WalletAlreadyExistsError()

            wallet = await uow.wallets.wallets.create({
                "user_id": user_id,
                "wallet_type": WalletType.CUSTOMER,
                "wallet_status": WalletStatus.ACTIVE,
                "available_balance": Decimal("0.00"),
                "pending_balance": Decimal("0.00"),
                "locked_balance": Decimal("0.00"),
                "promotional_balance": Decimal("0.00"),
                "reward_points": 0,
                "lifetime_credits": Decimal("0.00"),
                "lifetime_debits": Decimal("0.00"),
                "lifetime_cashback": Decimal("0.00"),
            })
            return WalletResponse.model_validate(wallet)

    async def get_wallet(self, user_id: uuid.UUID) -> WalletResponse:
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.find_by_user(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")
            return WalletResponse.model_validate(wallet)

    async def get_wallet_by_id(
        self, wallet_id: uuid.UUID, user_id: uuid.UUID
    ) -> WalletResponse:
        async with self._uow() as uow:
            wallet = await validate_wallet_owned_by_user(wallet_id, user_id, uow)
            return WalletResponse.model_validate(wallet)

    # ── Balance Operations ────────────────────────────────────────────────────

    async def credit_wallet(
        self,
        user_id: uuid.UUID,
        amount: Decimal,
        description: str,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
    ) -> WalletTransactionResponse:
        """
        Credit user wallet with SELECT FOR UPDATE to prevent concurrent races.
        Validates per-transaction and max-balance limits before committing.
        """
        validate_credit_amount(amount)

        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.get_by_user_with_lock(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")

            if wallet.wallet_status == WalletStatus.FROZEN:
                raise WalletFrozenError()
            if wallet.wallet_status == WalletStatus.SUSPENDED:
                raise WalletSuspendedError()
            if wallet.wallet_status == WalletStatus.CLOSED:
                raise WalletClosedError()

            new_balance = wallet.available_balance + amount
            if new_balance > MAX_WALLET_BALANCE:
                raise WalletBalanceLimitError(
                    f"Credit would exceed maximum wallet balance of ₹{MAX_WALLET_BALANCE}."
                )

            balance_before = wallet.available_balance
            await uow.wallets.wallets.update(wallet, {
                "available_balance": new_balance,
                "lifetime_credits": wallet.lifetime_credits + amount,
                "last_transaction_at": datetime.now(tz=timezone.utc),
            })

            txn = await uow.wallets.transactions.create({
                "wallet_id": wallet.id,
                "transaction_type": WalletTransactionType.CREDIT,
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": new_balance,
                "description": description,
                "reference_id": reference_id,
                "reference_type": reference_type,
            })

            return WalletTransactionResponse.model_validate(txn)

    async def debit_wallet(
        self,
        user_id: uuid.UUID,
        amount: Decimal,
        description: str,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
    ) -> WalletTransactionResponse:
        """
        Debit user wallet with SELECT FOR UPDATE.
        Validates status, minimum debit, and sufficient balance before committing.
        """
        if amount < MIN_WALLET_DEBIT:
            raise BusinessRuleError(
                f"Debit amount must be at least ₹{MIN_WALLET_DEBIT}."
            )

        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.get_by_user_with_lock(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")

            if wallet.wallet_status != WalletStatus.ACTIVE:
                if wallet.wallet_status == WalletStatus.FROZEN:
                    raise WalletFrozenError()
                if wallet.wallet_status == WalletStatus.SUSPENDED:
                    raise WalletSuspendedError()
                raise WalletClosedError()

            if wallet.is_on_hold:
                raise BusinessRuleError("Wallet is on emergency hold; debits are blocked.")

            validate_sufficient_balance(wallet, amount)

            balance_before = wallet.available_balance
            new_balance = balance_before - amount
            await uow.wallets.wallets.update(wallet, {
                "available_balance": new_balance,
                "lifetime_debits": wallet.lifetime_debits + amount,
                "last_transaction_at": datetime.now(tz=timezone.utc),
            })

            txn = await uow.wallets.transactions.create({
                "wallet_id": wallet.id,
                "transaction_type": WalletTransactionType.DEBIT,
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": new_balance,
                "description": description,
                "reference_id": reference_id,
                "reference_type": reference_type,
            })

            return WalletTransactionResponse.model_validate(txn)

    # ── Admin Wallet Operations ───────────────────────────────────────────────

    async def freeze_wallet(
        self, wallet_id: uuid.UUID, admin_id: uuid.UUID, reason: str
    ) -> WalletResponse:
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.get_by_id(wallet_id)
            if wallet is None:
                raise WalletNotFoundError(str(wallet_id))
            if wallet.wallet_status == WalletStatus.CLOSED:
                raise WalletClosedError("Cannot freeze a closed wallet.")
            updated = await uow.wallets.wallets.update(wallet, {
                "wallet_status": WalletStatus.FROZEN,
            })
            return WalletResponse.model_validate(updated)

    async def unfreeze_wallet(
        self, wallet_id: uuid.UUID, admin_id: uuid.UUID
    ) -> WalletResponse:
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.get_by_id(wallet_id)
            if wallet is None:
                raise WalletNotFoundError(str(wallet_id))
            if wallet.wallet_status != WalletStatus.FROZEN:
                raise BusinessRuleError("Wallet is not frozen.")
            updated = await uow.wallets.wallets.update(wallet, {
                "wallet_status": WalletStatus.ACTIVE,
            })
            return WalletResponse.model_validate(updated)

    async def close_wallet(
        self, wallet_id: uuid.UUID, admin_id: uuid.UUID
    ) -> WalletResponse:
        """Cannot close a wallet with a positive balance."""
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.get_by_id(wallet_id)
            if wallet is None:
                raise WalletNotFoundError(str(wallet_id))
            if wallet.available_balance > Decimal("0.00"):
                raise BusinessRuleError(
                    f"Wallet balance must be zero before closing. "
                    f"Current balance: ₹{wallet.available_balance}."
                )
            updated = await uow.wallets.wallets.update(wallet, {
                "wallet_status": WalletStatus.CLOSED,
            })
            return WalletResponse.model_validate(updated)

    # ── Transaction History ───────────────────────────────────────────────────

    async def list_transactions(
        self,
        user_id: uuid.UUID,
        filters: WalletTransactionFilters,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage[WalletTransactionResponse]:
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.find_by_user(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")
            txns = await uow.wallets.transactions.find_by_wallet(
                wallet.id, skip=0, limit=limit
            )
            items = [WalletTransactionResponse.model_validate(t) for t in txns]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_transaction(
        self, user_id: uuid.UUID, tx_id: uuid.UUID
    ) -> WalletTransactionResponse:
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.find_by_user(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")
            txn = await uow.wallets.transactions.get_by_id(tx_id)
            if txn is None or txn.wallet_id != wallet.id:
                raise BusinessRuleError("Transaction not found for this user.")
            return WalletTransactionResponse.model_validate(txn)

    # ── Rewards ───────────────────────────────────────────────────────────────

    async def award_reward(
        self, user_id: uuid.UUID, data: UserRewardCreate
    ) -> UserRewardResponse:
        """Create a UserReward with status=PENDING."""
        async with self._uow() as uow:
            wallet = await uow.wallets.wallets.find_by_user(user_id)
            if wallet is None:
                raise WalletNotFoundError(f"user_id={user_id}")

            reward = await uow.wallets.rewards.create({
                **data.model_dump(exclude_unset=True),
                "user_id": user_id,
                "wallet_id": wallet.id,
                "reward_status": UserRewardStatus.PENDING,
                "monetary_value": data.amount,
                "title": data.description or str(data.reward_type),
            })
            return UserRewardResponse.model_validate(reward)

    async def activate_reward(
        self, reward_id: uuid.UUID, admin_id: uuid.UUID
    ) -> UserRewardResponse:
        """
        Transition reward PENDING → ACTIVE.
        If reward type is CASHBACK and is_auto_credited, credit the wallet immediately.
        """
        async with self._uow() as uow:
            reward = await uow.wallets.rewards.get_by_id(reward_id)
            if reward is None:
                raise RewardNotFoundError(str(reward_id))

            if reward.reward_status != UserRewardStatus.PENDING:
                raise BusinessRuleError(
                    f"Reward is not in PENDING state (current: {reward.reward_status})."
                )

            updated_fields: dict = {"reward_status": UserRewardStatus.ACTIVE}

            if reward.is_auto_credited and reward.monetary_value > Decimal("0.00"):
                wallet = await uow.wallets.wallets.get_with_lock(reward.wallet_id)
                if wallet is None:
                    raise WalletNotFoundError(str(reward.wallet_id))

                new_balance = wallet.available_balance + reward.monetary_value
                if new_balance > MAX_WALLET_BALANCE:
                    raise WalletBalanceLimitError()

                balance_before = wallet.available_balance
                await uow.wallets.wallets.update(wallet, {
                    "available_balance": new_balance,
                    "lifetime_credits": wallet.lifetime_credits + reward.monetary_value,
                    "last_transaction_at": datetime.now(tz=timezone.utc),
                })

                txn = await uow.wallets.transactions.create({
                    "wallet_id": wallet.id,
                    "transaction_type": WalletTransactionType.CREDIT,
                    "amount": reward.monetary_value,
                    "balance_before": balance_before,
                    "balance_after": new_balance,
                    "description": f"Reward credited: {reward.title}",
                    "reference_id": reward.id,
                    "reference_type": "reward",
                })
                updated_fields["wallet_transaction_id"] = txn.id

            updated = await uow.wallets.rewards.update(reward, updated_fields)
            return UserRewardResponse.model_validate(updated)

    async def redeem_reward(
        self, reward_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserRewardResponse:
        """
        Validate and redeem a reward: ACTIVE → USED, credit wallet with reward value.
        """
        async with self._uow() as uow:
            reward = await validate_reward_redeemable(reward_id, user_id, uow)

            wallet = await uow.wallets.wallets.get_with_lock(reward.wallet_id)
            if wallet is None:
                raise WalletNotFoundError(str(reward.wallet_id))

            now = datetime.now(tz=timezone.utc)
            credit_amount = reward.monetary_value

            if credit_amount > Decimal("0.00"):
                new_balance = wallet.available_balance + credit_amount
                if new_balance > MAX_WALLET_BALANCE:
                    raise WalletBalanceLimitError()

                balance_before = wallet.available_balance
                await uow.wallets.wallets.update(wallet, {
                    "available_balance": new_balance,
                    "lifetime_credits": wallet.lifetime_credits + credit_amount,
                    "last_transaction_at": now,
                })

                txn = await uow.wallets.transactions.create({
                    "wallet_id": wallet.id,
                    "transaction_type": WalletTransactionType.CREDIT,
                    "amount": credit_amount,
                    "balance_before": balance_before,
                    "balance_after": new_balance,
                    "description": f"Reward redeemed: {reward.title}",
                    "reference_id": reward.id,
                    "reference_type": "reward",
                })

            updated = await uow.wallets.rewards.update(reward, {
                "reward_status": UserRewardStatus.USED,
                "used_at": now,
            })
            return UserRewardResponse.model_validate(updated)

    async def expire_rewards_batch(self, cutoff_date: datetime) -> int:
        """
        Mark all ACTIVE/PENDING rewards with expires_at <= cutoff_date as EXPIRED.
        Returns the count of rewards expired. Intended for background job use.
        """
        from app.models.wallets.reward import UserReward
        count = 0
        async with self._uow() as uow:
            # Fetch expired rewards in bulk via repo
            stmt_results = await uow.wallets.rewards.find_many(
                UserReward.reward_status.in_([
                    UserRewardStatus.ACTIVE,
                    UserRewardStatus.PENDING,
                ]),
                UserReward.expires_at.is_not(None),
                UserReward.expires_at <= cutoff_date,
                limit=5000,
            )
            for reward in stmt_results:
                await uow.wallets.rewards.update(reward, {
                    "reward_status": UserRewardStatus.EXPIRED,
                })
                count += 1
        return count

    async def list_rewards(
        self,
        user_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage[UserRewardResponse]:
        async with self._uow() as uow:
            rewards = await uow.wallets.rewards.find_by_user(user_id, skip=0, limit=limit)
            items = [UserRewardResponse.model_validate(r) for r in rewards]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_reward_balance(self, user_id: uuid.UUID) -> RewardBalanceResponse:
        """Sum of monetary_value across all ACTIVE, non-expired rewards."""
        async with self._uow() as uow:
            active_rewards = await uow.wallets.rewards.find_active_for_user(user_id)
            total = sum(
                (r.monetary_value for r in active_rewards),
                Decimal("0.00"),
            )
            return RewardBalanceResponse(
                user_id=user_id,
                total_active_value=total,
                active_reward_count=len(active_rewards),
            )
