"""
Wallet repository — Wallet, WalletTransaction, UserReward.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import WalletTransactionType
from app.models.wallets.reward import UserReward
from app.models.wallets.transaction import WalletTransaction
from app.models.wallets.wallet import Wallet
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Wallet)

    async def find_by_user(self, user_id: uuid.UUID) -> Wallet | None:
        return await self.find_one(Wallet.user_id == user_id)

    async def find_by_user_or_raise(self, user_id: uuid.UUID) -> Wallet:
        from app.repositories.base import NotFoundError
        wallet = await self.find_by_user(user_id)
        if wallet is None:
            raise NotFoundError("Wallet", f"user_id={user_id}")
        return wallet

    async def get_with_lock(self, wallet_id: uuid.UUID) -> Wallet | None:
        """Acquire a SELECT FOR UPDATE row-level lock for balance mutations."""
        from sqlalchemy import select as sa_select
        from sqlalchemy.dialects.postgresql import ARRAY
        stmt = (
            sa_select(Wallet)
            .where(Wallet.id == wallet_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_with_lock(self, user_id: uuid.UUID) -> Wallet | None:
        """Acquire a SELECT FOR UPDATE lock via user_id lookup."""
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_frozen(self) -> list[Wallet]:
        return await self.find_many(Wallet.wallet_status == "frozen")

    async def find_with_positive_pending(self) -> list[Wallet]:
        return await self.find_many(Wallet.pending_balance > 0)


class WalletTransactionRepository(BaseRepository[WalletTransaction]):
    """
    WalletTransaction is an immutable append-only ledger.
    No soft_delete, update, or delete operations should be used.
    Corrections are reversal transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WalletTransaction)

    async def find_by_wallet(
        self,
        wallet_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[WalletTransaction]:
        return await self.find_many(
            WalletTransaction.wallet_id == wallet_id,
            order_by=WalletTransaction.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_type(
        self,
        wallet_id: uuid.UUID,
        transaction_type: WalletTransactionType,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[WalletTransaction]:
        return await self.find_many(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.transaction_type == transaction_type,
            order_by=WalletTransaction.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_reference(
        self,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> list[WalletTransaction]:
        return await self.find_many(
            WalletTransaction.reference_type == reference_type,
            WalletTransaction.reference_id == reference_id,
        )

    async def find_recent(
        self,
        wallet_id: uuid.UUID,
        since: datetime,
    ) -> list[WalletTransaction]:
        return await self.find_many(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.created_at >= since,
            order_by=WalletTransaction.created_at.desc(),
        )

    async def find_pending(self, wallet_id: uuid.UUID) -> list[WalletTransaction]:
        return await self.find_many(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.transaction_status == "pending",
        )


class UserRewardRepository(BaseRepository[UserReward]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserReward)

    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserReward]:
        return await self.find_many(
            UserReward.user_id == user_id,
            order_by=UserReward.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_active_for_user(self, user_id: uuid.UUID) -> list[UserReward]:
        from app.models.wallets.reward import UserRewardStatus
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            UserReward.user_id == user_id,
            UserReward.reward_status == UserRewardStatus.ACTIVE,
            (UserReward.expires_at.is_(None)) | (UserReward.expires_at > now),
        )

    async def find_expiring_soon(self, user_id: uuid.UUID, before: datetime) -> list[UserReward]:
        from app.models.wallets.reward import UserRewardStatus
        return await self.find_many(
            UserReward.user_id == user_id,
            UserReward.reward_status == UserRewardStatus.ACTIVE,
            UserReward.expires_at.is_not(None),
            UserReward.expires_at <= before,
        )

    async def find_by_source(
        self,
        user_id: uuid.UUID,
        source_type: str,
    ) -> list[UserReward]:
        return await self.find_many(
            UserReward.user_id == user_id,
            UserReward.source_type == source_type,
        )


class WalletRepositoryAggregate:
    """Groups wallet-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.wallets = WalletRepository(session)
        self.transactions = WalletTransactionRepository(session)
        self.rewards = UserRewardRepository(session)
