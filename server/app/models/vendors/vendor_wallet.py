"""
VendorWallet — financial ledger for vendor earnings and settlement balances.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor
    from app.models.vendors.vendor_settlement import VendorSettlement


class VendorWallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Financial account tracking a vendor's earnings on the Tyohaar platform.

    One wallet per vendor, created automatically on vendor approval.

    Balance semantics:
    - `balance`:                  Current available balance (cleared, not yet paid out)
    - `pending_settlement_amount`: Earnings from completed bookings awaiting settlement cycle
    - `lifetime_earnings`:         Running total of all gross earnings (never decremented)
    - `total_paid_out`:            Running total of all successful payouts to the vendor

    The relationship: lifetime_earnings = total_paid_out + balance + pending_settlement_amount
    (approximately, modulo fees/adjustments)

    All amount columns use Numeric(15, 2) to avoid floating-point rounding errors
    in financial calculations.
    """

    __tablename__ = "vendor_wallets"

    __table_args__ = (
        UniqueConstraint("vendor_id", name="uq_vendor_wallets_vendor_id"),
        CheckConstraint("balance >= 0", name="ck_vendor_wallets_balance_non_negative"),
        CheckConstraint("pending_settlement_amount >= 0", name="ck_vendor_wallets_pending_non_negative"),
        CheckConstraint("lifetime_earnings >= 0", name="ck_vendor_wallets_lifetime_non_negative"),
        CheckConstraint("total_paid_out >= 0", name="ck_vendor_wallets_paid_out_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    # ── Balances ──────────────────────────────────────────────────────────────

    balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Available balance cleared for payout (INR)",
    )

    pending_settlement_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment=(
            "Earnings from completed bookings not yet processed in a settlement cycle. "
            "Moves to balance after the settlement run."
        ),
    )

    lifetime_earnings: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative gross earnings since vendor activation. Never decremented.",
    )

    total_paid_out: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative total of all payouts successfully transferred to the vendor.",
    )

    # ── Activity ──────────────────────────────────────────────────────────────

    last_settlement_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent successful settlement payout",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inactive wallets block new settlements. Set False for suspended vendors.",
    )

    is_on_hold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "When True, no payouts are processed regardless of balance. "
            "Used during dispute resolution or compliance holds."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="wallet")

    settlements: Mapped[list[VendorSettlement]] = relationship(
        "VendorSettlement",
        back_populates="wallet",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<VendorWallet vendor_id={self.vendor_id} "
            f"balance={self.balance} pending={self.pending_settlement_amount}>"
        )
