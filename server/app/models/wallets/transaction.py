"""
WalletTransaction — immutable ledger of every balance change in a customer wallet.

Every credit, debit, cashback, reward, or adjustment must produce exactly one
WalletTransaction. Rows are NEVER updated or deleted after creation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import WalletTransactionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.wallets.wallet import Wallet
    from app.models.users.user import User


class WalletTransactionStatus(str, enum.Enum):
    """
    Processing state of a single wallet transaction.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"        # Initiated but not yet applied to balance
    COMPLETED = "completed"    # Balance updated; balance_after is final
    FAILED = "failed"          # Transaction did not complete; balance unchanged
    REVERSED = "reversed"      # Completed then reversed by a subsequent transaction


class WalletTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single immutable entry in the wallet balance ledger.

    Every balance change (credit, debit, cashback, adjustment, expiry, etc.)
    must produce one WalletTransaction row. This ensures the wallet balance
    can always be fully reconstructed by replaying transactions.

    IMMUTABILITY: This table must have NO UPDATE or DELETE permissions in
    production. Corrections are made by creating reversal transactions (type=EXPIRY
    or a new ADJUSTMENT with a negative amount), never by editing rows.

    `reference_type` + `reference_id` form a polymorphic pointer to the source:
    - "booking"    → bookings.id
    - "refund"     → refunds.id
    - "reward"     → user_rewards.id
    - "payment"    → payments.id
    - "membership" → user_memberships.id
    - "admin"      → NULL (manual adjustment by staff)
    - "referral"   → referrals.id (future)

    `balance_before` and `balance_after` record the `available_balance` snapshot
    at the moment of the transaction. For pending→completed transitions,
    balance_after reflects the final cleared state.

    `initiated_by_id` is NULL for system-generated transactions (cashback, expiry)
    and set to the admin user's ID for manual adjustments.
    """

    __tablename__ = "wallet_transactions"

    __table_args__ = (
        Index("ix_wallet_tx_wallet_id", "wallet_id"),
        Index("ix_wallet_tx_type", "wallet_id", "transaction_type"),
        Index("ix_wallet_tx_reference", "reference_type", "reference_id"),
        Index("ix_wallet_tx_status", "transaction_status"),
        Index("ix_wallet_tx_initiated_at", "initiated_at"),
        CheckConstraint("amount != 0", name="ck_wallet_tx_amount_nonzero"),
        CheckConstraint("balance_before >= 0", name="ck_wallet_tx_balance_before_non_negative"),
        CheckConstraint("balance_after >= 0", name="ck_wallet_tx_balance_after_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Wallet whose balance this transaction affects.",
    )

    # ── Type & Amount ─────────────────────────────────────────────────────────

    transaction_type: Mapped[WalletTransactionType] = mapped_column(
        SAEnum(WalletTransactionType, name="wallet_transaction_type", native_enum=False),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment=(
            "Signed amount: positive for credits, negative for debits. "
            "CHECK ensures nonzero — zero-amount transactions are never created."
        ),
    )

    # ── Balance Snapshot ──────────────────────────────────────────────────────

    balance_before: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Wallet available_balance immediately before this transaction.",
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Wallet available_balance immediately after this transaction completes.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    transaction_status: Mapped[WalletTransactionStatus] = mapped_column(
        SAEnum(WalletTransactionStatus, name="wallet_transaction_status", native_enum=False),
        nullable=False,
        default=WalletTransactionStatus.PENDING,
    )

    # ── Source Reference (polymorphic) ────────────────────────────────────────

    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Entity type that caused this transaction: booking, refund, reward, payment, etc.",
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the source entity. Not a FK to allow cross-domain flexibility.",
    )

    # ── Description & Context ─────────────────────────────────────────────────

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Human-readable description shown in the wallet statement to the customer.",
    )

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured context for internal use: gateway refs, promo codes, "
            "admin override justification, etc."
        ),
    )

    # ── Actor ─────────────────────────────────────────────────────────────────

    initiated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Admin or staff user who triggered this transaction. "
            "NULL for system-generated transactions (cashback, auto-expiry)."
        ),
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the transaction was created.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the transaction was confirmed and balance_after became effective.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    wallet: Mapped[Wallet] = relationship(
        "Wallet",
        back_populates="transactions",
        lazy="noload",
    )

    initiated_by: Mapped[User | None] = relationship(
        "User",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<WalletTransaction id={self.id} wallet_id={self.wallet_id} "
            f"type={self.transaction_type} amount={self.amount} status={self.transaction_status}>"
        )
