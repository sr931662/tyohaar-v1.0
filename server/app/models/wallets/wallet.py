"""
Wallet — virtual credit balance maintained by Tyohaar for a customer.

Separate from payment gateway records. Funds enter via cashback, refunds,
rewards, and promotional credits. Funds exit via booking payments and withdrawals.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, WalletType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.wallets.transaction import WalletTransaction
    from app.models.wallets.reward import UserReward


class WalletStatus(str, enum.Enum):
    """
    Operational state of a customer wallet.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    ACTIVE = "active"
    FROZEN = "frozen"          # Temporary admin hold — reads allowed, writes blocked
    SUSPENDED = "suspended"    # Policy violation — no credits or debits
    CLOSED = "closed"          # Account deactivated; balance must be zero


class Wallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Virtual credit wallet for a Tyohaar customer.

    Design:
    - One wallet per customer (enforced by UNIQUE on user_id).
    - Balances are denormalized for fast reads; the source of truth is the
      append-only WalletTransaction ledger, which can always reconstruct them.
    - `available_balance` is the only amount a customer can spend.
    - `pending_balance` enters the available pool after clearance (e.g., after
      a booking's refund is confirmed by the payment gateway).
    - `locked_balance` is reserved mid-transaction and released on completion or failure.
    - `promotional_balance` holds platform-issued promotional credits that may
      expire; tracked separately so expiry logic can target only this bucket.

    Balance invariant (maintained by service layer):
        available_balance + pending_balance + locked_balance ≥ 0
        lifetime_credits = lifetime_debits + available_balance + pending_balance + locked_balance
        (approximately, before promotional expiry)

    All monetary fields use Numeric(15, 2) to match VendorWallet precision and
    safely represent lifetime totals without overflow.
    """

    __tablename__ = "wallets"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_wallets_user_id"),
        CheckConstraint("available_balance >= 0", name="ck_wallets_available_non_negative"),
        CheckConstraint("pending_balance >= 0", name="ck_wallets_pending_non_negative"),
        CheckConstraint("locked_balance >= 0", name="ck_wallets_locked_non_negative"),
        CheckConstraint("promotional_balance >= 0", name="ck_wallets_promo_non_negative"),
        CheckConstraint("lifetime_credits >= 0", name="ck_wallets_lifetime_credits_non_negative"),
        CheckConstraint("lifetime_debits >= 0", name="ck_wallets_lifetime_debits_non_negative"),
        CheckConstraint("lifetime_cashback >= 0", name="ck_wallets_cashback_non_negative"),
        CheckConstraint("reward_points >= 0", name="ck_wallets_points_non_negative"),
        Index("ix_wallets_wallet_status", "wallet_status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        comment="Customer who owns this wallet. One wallet per customer.",
    )

    wallet_type: Mapped[WalletType] = mapped_column(
        SAEnum(WalletType, name="wallet_type", native_enum=False),
        nullable=False,
        default=WalletType.CUSTOMER,
        comment="CUSTOMER for all wallets in this domain. VendorWallet handles vendor balances.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    wallet_status: Mapped[WalletStatus] = mapped_column(
        SAEnum(WalletStatus, name="wallet_status", native_enum=False),
        nullable=False,
        default=WalletStatus.ACTIVE,
    )

    is_on_hold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Emergency hold: blocks all debits without changing wallet_status.",
    )

    # ── Active Balances ───────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
        comment="All monetary balances are denominated in this currency.",
    )

    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cleared credits available for spending at checkout.",
    )

    pending_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Credits awaiting clearance (e.g. refund pending gateway confirmation).",
    )

    locked_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Reserved mid-transaction; released on success or failure.",
    )

    promotional_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment=(
            "Platform-issued promotional credits. Tracked separately because "
            "they may carry expiry dates enforced by the UserReward model."
        ),
    )

    # ── Reward Points ─────────────────────────────────────────────────────────

    reward_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Integer loyalty point balance. Points are not directly spendable — "
            "they are converted to wallet credits by the redemption service."
        ),
    )

    # ── Lifetime Accumulators (never decremented) ─────────────────────────────

    lifetime_credits: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative monetary credits received since wallet creation.",
    )

    lifetime_debits: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative monetary debits (spends + withdrawals) since wallet creation.",
    )

    lifetime_cashback: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative cashback earned across all bookings.",
    )

    # ── Activity ──────────────────────────────────────────────────────────────

    last_transaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent WalletTransaction (credits or debits).",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    owner: Mapped[User] = relationship("User", lazy="noload")

    transactions: Mapped[List[WalletTransaction]] = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    rewards: Mapped[List[UserReward]] = relationship(
        "UserReward",
        back_populates="wallet",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Wallet id={self.id} user_id={self.user_id} "
            f"available={self.available_balance} status={self.wallet_status}>"
        )
