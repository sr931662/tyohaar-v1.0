"""
VendorSettlement — payout disbursement record for vendor earnings.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SettlementStatus
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorSettlement(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """
    A single payout disbursement from Tyohaar to a vendor.

    Amount breakdown (all in INR):
        gross_amount        = what the customer paid for the booking(s)
        commission_amount   = Tyohaar's commission (% of gross)
        platform_fee        = fixed platform processing fee
        tds_amount          = Tax Deducted at Source (Section 194C/O as applicable)
        gst_on_fee          = GST charged on platform fee + commission
        net_amount          = gross - commission - platform_fee - tds - gst_on_fee
                            = actual amount transferred to vendor's bank account

    A settlement can cover one booking (immediate) or multiple bookings
    within a settlement period (weekly/monthly batch). `booking_id` is
    nullable to support batch settlements; use a join table for multi-booking
    settlements when needed.

    `utr_number` (Unique Transaction Reference) is the RBI-mandated reference
    for NEFT/RTGS/IMPS transactions in India. Always record this for reconciliation.
    """

    __tablename__ = "vendor_settlements"

    __table_args__ = (
        Index("ix_vendor_settlements_vendor_id", "vendor_id"),
        Index("ix_vendor_settlements_wallet_id", "wallet_id"),
        Index("ix_vendor_settlements_status", "status"),
        Index("ix_vendor_settlements_payout_date", "payout_date"),
        Index("ix_vendor_settlements_period", "settlement_period_start", "settlement_period_end"),
        CheckConstraint("gross_amount >= 0", name="ck_settlement_gross_non_negative"),
        CheckConstraint("commission_amount >= 0", name="ck_settlement_commission_non_negative"),
        CheckConstraint("platform_fee >= 0", name="ck_settlement_platform_fee_non_negative"),
        CheckConstraint("tds_amount >= 0", name="ck_settlement_tds_non_negative"),
        CheckConstraint("gst_on_fee >= 0", name="ck_settlement_gst_non_negative"),
        CheckConstraint("net_amount >= 0", name="ck_settlement_net_non_negative"),
        CheckConstraint(
            "settlement_period_end >= settlement_period_start",
            name="ck_settlement_period_dates_order",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
    )

    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Legacy reference to the now-removed vendor wallet ledger. No longer an FK.",
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Set for single-booking settlements. NULL for batch period settlements.",
    )

    # ── Amount Breakdown ──────────────────────────────────────────────────────

    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total amount paid by the customer for the covered booking(s)",
    )

    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Tyohaar platform commission deducted from gross",
    )

    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Fixed platform processing/logistics fee",
    )

    tds_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Tax Deducted at Source (TDS) under applicable Indian Income Tax provisions",
    )

    gst_on_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="18% GST levied on platform fee and commission (reverse charge / forward charge)",
    )

    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount actually transferred to the vendor: gross - commission - fee - tds - gst",
    )

    # ── Settlement Period ─────────────────────────────────────────────────────

    settlement_period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="First day of the period covered by this settlement",
    )

    settlement_period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Last day of the period covered by this settlement (inclusive)",
    )

    # ── Payout Status ─────────────────────────────────────────────────────────

    status: Mapped[SettlementStatus] = mapped_column(
        SAEnum(SettlementStatus, name="settlement_status", native_enum=False),
        nullable=False,
        default=SettlementStatus.PENDING,
        index=True,
    )

    payout_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Calendar date on which the transfer was initiated",
    )

    # ── References & Reconciliation ───────────────────────────────────────────

    payout_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Tyohaar's internal payout batch reference ID",
    )

    bank_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Bank transaction ID / NEFT/RTGS transaction reference",
    )

    utr_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment=(
            "RBI Unique Transaction Reference number for NEFT/RTGS/IMPS. "
            "Mandatory for reconciliation in Indian banking."
        ),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about this settlement (adjustments, disputes, etc.)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="settlements")

    def __repr__(self) -> str:
        return (
            f"<VendorSettlement id={self.id} vendor_id={self.vendor_id} "
            f"net={self.net_amount} status={self.status}>"
        )
