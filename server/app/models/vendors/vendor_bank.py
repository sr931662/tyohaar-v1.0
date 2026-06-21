"""
VendorBankAccount — bank account details for vendor payout settlements.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import VerificationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorBankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A bank account registered by a vendor for receiving settlement payouts.

    Vendors may register multiple accounts but only one can be primary
    at any time. Settlements are always sent to the primary verified account.

    Security notes:
    - `account_number` should be stored encrypted at the application layer
      using AES-256 before being persisted here.
    - `cancelled_cheque_url` must resolve via signed URL only (private bucket).
    - Account verification requires a micro-deposit or Penny Drop API call
      (e.g., via Razorpay, Cashfree) before the account is used for payouts.
    """

    __tablename__ = "vendor_bank_accounts"

    __table_args__ = (
        Index("ix_vendor_bank_accounts_vendor_id", "vendor_id"),
        Index("ix_vendor_bank_accounts_primary", "vendor_id", "is_primary"),
        # Enforce exactly one primary account per vendor at DB level via partial unique index
        UniqueConstraint("vendor_id", "is_primary", name="uq_vendor_bank_one_primary"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Account Details ───────────────────────────────────────────────────────

    account_holder_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Account holder name exactly as registered with the bank",
    )

    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)

    bank_branch: Mapped[str | None] = mapped_column(String(200), nullable=True)

    account_number: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment=(
            "AES-256 encrypted account number. "
            "Decrypt only when preparing a payout request; never log or expose."
        ),
    )

    ifsc_code: Mapped[str] = mapped_column(
        String(11),
        nullable=False,
        comment="11-character IFSC code (e.g., SBIN0001234)",
    )

    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="savings",
        comment="'savings' or 'current'",
    )

    # ── UPI ───────────────────────────────────────────────────────────────────

    upi_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="UPI VPA (e.g., vendor@oksbi). Used for instant low-value payouts.",
    )

    # ── Verification ──────────────────────────────────────────────────────────

    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status", native_enum=False),
        nullable=False,
        default=VerificationStatus.PENDING,
    )

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Tyohaar staff or automated Penny Drop service that verified the account",
    )

    cancelled_cheque_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Private CDN reference to the uploaded cancelled cheque image",
    )

    # ── Flags ─────────────────────────────────────────────────────────────────

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Only the primary verified account receives settlement payouts",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="bank_accounts")

    def __repr__(self) -> str:
        return (
            f"<VendorBankAccount id={self.id} vendor_id={self.vendor_id} "
            f"bank={self.bank_name!r} primary={self.is_primary}>"
        )
