"""
Wallet domain — response (output) schemas.

These schemas are serialized to JSON and returned to API consumers.
Security rule: internal_notes, deleted_at are NEVER included here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, computed_field

from app.models.enums import Currency, RewardType, WalletTransactionType, WalletType
from app.models.wallets.wallet import WalletStatus
from app.schemas.base import BaseSchema, MoneyAmount

__all__ = [
    "WalletResponse",
    "WalletTransactionResponse",
    "UserRewardResponse",
]


class WalletResponse(BaseSchema):
    """
    Public wallet representation returned to authenticated customers and admin.

    Balance fields are read directly from denormalized columns — not recomputed
    on every request. The service layer is responsible for keeping them in sync
    with the ledger via WalletTransaction records.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    wallet_type: WalletType
    wallet_status: WalletStatus
    is_on_hold: bool
    currency: Currency
    available_balance: Decimal = Field(decimal_places=2)
    pending_balance: Decimal = Field(decimal_places=2)
    locked_balance: Decimal = Field(decimal_places=2)
    promotional_balance: Decimal = Field(decimal_places=2)
    reward_points: int = Field(ge=0)
    lifetime_credits: Decimal = Field(decimal_places=2)
    lifetime_debits: Decimal = Field(decimal_places=2)
    lifetime_cashback: Decimal = Field(decimal_places=2)
    last_transaction_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_spendable(self) -> Decimal:
        """Convenience: available + promotional balance."""
        return self.available_balance + self.promotional_balance


class WalletTransactionResponse(BaseSchema):
    """
    Immutable ledger entry returned in wallet statement endpoints.

    Transactions cannot be deleted or modified (except description).
    The balance_before / balance_after fields provide a full audit trail.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    wallet_id: uuid.UUID
    transaction_type: WalletTransactionType
    amount: Decimal = Field(decimal_places=2, ge=Decimal("0"))
    balance_before: Decimal = Field(decimal_places=2)
    balance_after: Decimal = Field(decimal_places=2)
    description: str | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    created_at: datetime


class UserRewardResponse(BaseSchema):
    """
    Reward grant record shown in the rewards history screen.

    is_credited indicates whether the reward has been applied to the wallet.
    credited_at is None until the reward processing job runs.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    wallet_id: uuid.UUID
    user_id: uuid.UUID
    reward_type: RewardType
    amount: Decimal = Field(decimal_places=2, ge=Decimal("0"))
    points: int | None = None
    description: str | None = None
    is_credited: bool
    credited_at: datetime | None = None
    expires_at: datetime | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    created_at: datetime
