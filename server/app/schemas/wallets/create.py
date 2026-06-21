"""
Wallet domain — create (input) schemas.

These schemas are used by the service layer and internal APIs to create
wallet records, log transactions, and credit rewards. They are NOT exposed
directly to end-user HTTP endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator

from app.models.enums import Currency, RewardType, WalletTransactionType, WalletType
from app.schemas.base import BaseSchema, MoneyAmount

__all__ = [
    "WalletCreate",
    "WalletTransactionCreate",
    "UserRewardCreate",
]


class WalletCreate(BaseSchema):
    """
    Input schema for provisioning a new customer wallet.

    Typically called by the user registration service immediately after
    a new user account is created.
    """

    user_id: uuid.UUID = Field(description="Owner of this wallet.")
    currency: Currency = Field(
        default=Currency.INR,
        description="ISO 4217 currency code; all balance fields denominated in this.",
    )
    wallet_type: WalletType = Field(
        default=WalletType.CUSTOMER,
        description="CUSTOMER for end-users; VENDOR is handled by VendorWallet.",
    )


class WalletTransactionCreate(BaseSchema):
    """
    Input schema for appending an immutable ledger entry.

    The service layer is responsible for computing balance_before and
    balance_after; these must be passed explicitly so the ledger is a
    faithful audit trail independent of ORM-level triggers.
    """

    wallet_id: uuid.UUID = Field(description="Wallet to which this transaction belongs.")
    transaction_type: WalletTransactionType = Field(
        description="Nature of the movement (CREDIT, DEBIT, REFUND, …).",
    )
    amount: MoneyAmount = Field(
        description="Absolute value of the transaction. Always positive.",
    )
    balance_before: Annotated[Decimal, Field(decimal_places=2)] = Field(
        description="Wallet available_balance immediately before this transaction.",
    )
    balance_after: Annotated[Decimal, Field(decimal_places=2)] = Field(
        description="Wallet available_balance immediately after this transaction.",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable description shown in wallet statement.",
    )
    reference_type: str | None = Field(
        default=None,
        max_length=100,
        description="Entity type linked to this transaction, e.g. 'booking', 'refund'.",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the linked entity (booking_id, refund_id, etc.).",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Only relevant for promotional CREDIT entries that expire.",
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Transaction amount must be strictly positive.")
        return v


class UserRewardCreate(BaseSchema):
    """
    Input schema for recording a reward grant to a user's wallet.

    Rewards begin as un-credited (is_credited=False) until the reward
    processing job confirms and credits the wallet balance.
    """

    wallet_id: uuid.UUID = Field(description="Target wallet for the reward.")
    user_id: uuid.UUID = Field(description="Beneficiary user.")
    reward_type: RewardType = Field(description="Category of reward being granted.")
    amount: MoneyAmount = Field(
        description="Monetary value of the reward (or points face value for LOYALTY_POINTS).",
    )
    points: Annotated[int, Field(ge=0)] | None = Field(
        default=None,
        description="Integer point grant, populated only for LOYALTY_POINTS rewards.",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Context visible in the rewards history screen.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Date after which uncredited promotional rewards lapse.",
    )
    reference_type: str | None = Field(
        default=None,
        max_length=100,
        description="Entity type that triggered this reward, e.g. 'booking'.",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the triggering entity.",
    )
