"""
PaymentSplit — internal settlement allocation for a payment.

Defines how a customer payment is distributed across platform, vendor,
taxes, and future partner payouts. INTERNAL ONLY.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SettlementStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.payment import Payment
    from app.models.vendors.vendor import Vendor


class SplitType(str, enum.Enum):
    """
    Category of recipient for a payment split.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PLATFORM = "platform"    # Tyohaar's commission/fee portion
    VENDOR = "vendor"        # Portion payable to a vendor
    TAX = "tax"              # GST / TDS collected for remittance
    PARTNER = "partner"      # Future: white-label partner revenue share


class PaymentSplit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single allocation record within a payment settlement plan.

    When a customer payment is captured, the service layer creates split records
    that define how the total amount flows:
    - PLATFORM split → Tyohaar's margin
    - VENDOR split(s) → amounts owed to each vendor (one per assigned vendor)
    - TAX split → collected GST/TDS to be remitted to the government

    INTERNAL: Split records drive VendorSettlement creation and accounting.
    Customers and vendors do NOT see split details.

    `vendor_id` is set only for VENDOR type splits. All other types have NULL vendor.
    `settlement_status` tracks whether this split has been settled/paid.
    """

    __tablename__ = "payment_splits"

    __table_args__ = (
        Index("ix_payment_splits_payment_id", "payment_id"),
        Index("ix_payment_splits_vendor_id", "vendor_id"),
        Index("ix_payment_splits_settlement_status", "settlement_status"),
        CheckConstraint("amount >= 0", name="ck_payment_split_amount_non_negative"),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="ck_payment_split_percentage_range",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Recipient ─────────────────────────────────────────────────────────────

    split_type: Mapped[SplitType] = mapped_column(
        SAEnum(SplitType, name="split_type", native_enum=False),
        nullable=False,
    )

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Set only for VENDOR split type. INTERNAL — never expose to customers.",
    )

    # ── Amount ────────────────────────────────────────────────────────────────

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Absolute amount allocated to this recipient",
    )

    percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage of total payment this split represents (informational)",
    )

    description: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Internal description e.g. 'Commission 15%' or 'CGST 9%'",
    )

    # ── Settlement ────────────────────────────────────────────────────────────

    settlement_status: Mapped[SettlementStatus] = mapped_column(
        SAEnum(SettlementStatus, name="settlement_status", native_enum=False),
        nullable=False,
    )

    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this split was transferred to the recipient",
    )

    settlement_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="UTR number or internal settlement batch reference",
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment] = relationship(
        "Payment",
        back_populates="splits",
        lazy="noload",
    )

    vendor: Mapped[Vendor | None] = relationship("Vendor", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<PaymentSplit id={self.id} payment_id={self.payment_id} "
            f"type={self.split_type} amount={self.amount} status={self.settlement_status}>"
        )
