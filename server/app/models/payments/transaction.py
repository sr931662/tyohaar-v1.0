"""
Transaction — the immutable platform-level financial ledger.

Records every money movement on the Tyohaar platform: customer payments,
vendor settlements, platform fee collections, refund disbursements, and
manual adjustments. Distinct from PaymentTransaction (gateway API interactions)
and WalletTransaction (virtual wallet balance changes).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, SettlementStatus, TransactionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.payments.payment import Payment


class TransactionDirection(str, enum.Enum):
    """
    Direction of money movement from the platform's perspective.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CREDIT = "credit"   # Money flowing INTO Tyohaar or INTO a customer/vendor account
    DEBIT = "debit"     # Money flowing OUT OF Tyohaar or OUT OF a customer/vendor account


class ReconciliationStatus(str, enum.Enum):
    """
    Reconciliation state of a financial transaction.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"         # Not yet reconciled against bank/gateway statement
    RECONCILED = "reconciled"   # Matched to a bank/gateway record
    UNMATCHED = "unmatched"     # Bank record found but no matching platform transaction
    FLAGGED = "flagged"         # Discrepancy detected; requires finance team review
    WAIVED = "waived"           # Manually waived after investigation


class PartyType(str, enum.Enum):
    """
    Type of party involved in a financial transaction (payer or payee).
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CUSTOMER = "customer"       # references users.id
    VENDOR = "vendor"           # references vendors.id
    PLATFORM = "platform"       # Tyohaar itself (no external entity FK)
    EXTERNAL = "external"       # Bank, payment gateway, or third-party


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An immutable record in the Tyohaar platform financial ledger.

    Rows are APPEND-ONLY and must never be updated or deleted.
    Every confirmed money movement — regardless of direction or domain —
    must produce exactly one Transaction row.

    Relationship to other financial tables:
    - `PaymentTransaction` (payment_transactions): gateway API interaction logs.
      Captures each HTTP round-trip to Razorpay/Stripe/etc.
    - `WalletTransaction` (wallet_transactions): virtual wallet balance changes.
      Captures credits/debits to customer wallet buckets.
    - `Transaction` (this table): canonical accounting ledger. Captures the
      economic reality of money moving between parties, regardless of the
      mechanism. A single customer payment may produce:
        1. PaymentTransaction (gateway capture record)
        2. Transaction[PAYMENT]      (customer → Tyohaar)
        3. Transaction[FEE]          (Tyohaar platform fee entry)
        4. Transaction[COMMISSION]   (vendor payout allocation)

    Polymorphic payer/payee:
    - `payer_type` + `payer_id`: who the money is leaving.
    - `payee_type` + `payee_id`: who the money is going to.
    - Both use PartyType and store UUIDs without FK constraints to allow
      cross-domain references (e.g., vendor IDs from the vendors table).
    - For PLATFORM party type, the corresponding `_id` is NULL.

    Settlement:
    - `settlement_status` tracks whether Tyohaar has settled with the payee.
    - `settlement_batch_id` groups transactions settled in the same payout batch.
    - `settled_at` records when funds were actually disbursed.

    Reversal:
    - Corrections are made by creating a new Transaction with is_reversal=True
      referencing the original via `reversal_of_id`. Never edit or delete rows.

    `gateway_reference` stores the external payment system's reference
    (e.g., Razorpay transfer_id, NEFT UTR number, bank batch reference).

    `context_data` stores structured context for audit and reconciliation:
        {
          "booking_number": "TYH-20240615-001234",
          "invoice_number": "INV-2024-MEM-001234",
          "gateway": "razorpay",
          "settlement_cycle": "D+2"
        }
    """

    __tablename__ = "transactions"

    __table_args__ = (
        UniqueConstraint("transaction_number", name="uq_transactions_transaction_number"),
        Index("ix_transactions_type", "transaction_type"),
        Index("ix_transactions_payer", "payer_type", "payer_id"),
        Index("ix_transactions_payee", "payee_type", "payee_id"),
        Index("ix_transactions_payment_id", "payment_id"),
        Index("ix_transactions_booking_id", "booking_id"),
        Index("ix_transactions_settlement_status", "settlement_status"),
        Index("ix_transactions_reconciliation", "reconciliation_status"),
        Index("ix_transactions_transacted_at", "transacted_at"),
        Index("ix_transactions_settlement_batch", "settlement_batch_id"),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    transaction_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment=(
            "Unique human-readable reference e.g. TXN-2024-001234. "
            "Generated by service layer before insert."
        ),
    )

    # ── Transaction Classification ────────────────────────────────────────────

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", native_enum=False),
        nullable=False,
    )

    direction: Mapped[TransactionDirection] = mapped_column(
        SAEnum(TransactionDirection, name="transaction_direction", native_enum=False),
        nullable=False,
        comment="CREDIT = money in; DEBIT = money out (from the platform's perspective).",
    )

    # ── Amount ────────────────────────────────────────────────────────────────

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Absolute (always positive) transaction amount in `currency`.",
    )

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    # ── Parties (polymorphic) ─────────────────────────────────────────────────

    payer_type: Mapped[PartyType] = mapped_column(
        SAEnum(PartyType, name="party_type", native_enum=False),
        nullable=False,
        comment="Type of the entity sending money.",
    )

    payer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the payer entity. NULL when payer_type=PLATFORM.",
    )

    payee_type: Mapped[PartyType] = mapped_column(
        SAEnum(PartyType, name="party_type", native_enum=False),
        nullable=False,
        comment="Type of the entity receiving money.",
    )

    payee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the payee entity. NULL when payee_type=PLATFORM.",
    )

    # ── Context References ────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Associated booking for booking-related transactions.",
    )

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=True,
        comment="The Payment record that triggered this transaction.",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Human-readable transaction summary for finance statements.",
    )

    # ── Settlement ────────────────────────────────────────────────────────────

    settlement_status: Mapped[SettlementStatus] = mapped_column(
        SAEnum(SettlementStatus, name="settlement_status", native_enum=False),
        nullable=False,
        default=SettlementStatus.PENDING,
    )

    settlement_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "Groups all transactions settled in the same payout batch. "
            "Not a FK — batch tracking is handled by the finance service."
        ),
    )

    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When funds were actually disbursed to the payee.",
    )

    # ── External Reference ────────────────────────────────────────────────────

    gateway_reference: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment=(
            "External reference from the payment gateway or bank: "
            "Razorpay transfer_id, NEFT UTR, IMPS reference, bank batch ID."
        ),
    )

    # ── Reconciliation ────────────────────────────────────────────────────────

    reconciliation_status: Mapped[ReconciliationStatus] = mapped_column(
        SAEnum(ReconciliationStatus, name="reconciliation_status", native_enum=False),
        nullable=False,
        default=ReconciliationStatus.PENDING,
    )

    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the finance team reconciled this transaction against bank records.",
    )

    reconciled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who performed or confirmed the reconciliation.",
    )

    reconciliation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Finance team notes on reconciliation discrepancies or decisions.",
    )

    # ── Reversal ──────────────────────────────────────────────────────────────

    is_reversal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for correction entries that reverse a prior transaction. "
            "Always create a new reversal row — never edit the original."
        ),
    )

    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=True,
        comment="UUID of the original transaction this row reverses.",
    )

    reversal_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for reversing the original transaction.",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    transacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "Authoritative timestamp when the money movement occurred. "
            "May differ from created_at for async or backfilled records."
        ),
    )

    # ── Audit Metadata ────────────────────────────────────────────────────────

    context_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured audit context: booking_number, invoice_number, "
            "gateway, settlement_cycle, campaign_id, etc."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment | None] = relationship(
        "Payment",
        lazy="noload",
    )

    reconciled_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reconciled_by_id],
        lazy="noload",
    )

    reversal_of: Mapped[Transaction | None] = relationship(
        "Transaction",
        remote_side="Transaction.id",
        foreign_keys=[reversal_of_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} number={self.transaction_number!r} "
            f"type={self.transaction_type} dir={self.direction} amount={self.amount}>"
        )
