"""
Invoice — a generalized GST-compliant financial invoice for non-booking payments.

Covers memberships, vendor settlement disbursements, platform adjustment invoices,
and any other financial transaction that requires a formal billing document.
For booking-specific invoices see app/models/bookings/booking_invoice.py.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
from app.models.enums import Currency, InvoiceStatus
from app.models.mixins import NotesMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.payments.payment import Payment


class InvoiceEntityType(str, enum.Enum):
    """
    The platform domain that triggered this invoice.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    MEMBERSHIP = "membership"           # Membership subscription renewal or purchase
    VENDOR_SETTLEMENT = "vendor_settlement"  # Payout to a vendor after booking completion
    PLATFORM_ADJUSTMENT = "platform_adjustment"  # Manual credit/debit by Tyohaar finance
    CREDIT_NOTE = "credit_note"         # Formal credit note against a prior invoice
    OTHER = "other"


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, NotesMixin, Base):
    """
    A formal, GST-compliant financial invoice for non-booking transactions.

    This model complements BookingInvoice (which is booking-specific) by
    covering all other billable events on the platform:
    - Membership subscription invoices (monthly/annual renewals).
    - Vendor settlement disbursement records.
    - Platform fee adjustments (credits, penalties, corrections).
    - Future: credit notes against prior invoices.

    `invoice_number` follows the format INV-{YEAR}-{ENTITY_TYPE_PREFIX}-{SEQ}
    (e.g., INV-2024-MEM-001234) and is globally unique.

    GST fields:
    - `place_of_supply`: 2-letter state code (e.g., 'MH', 'KA') for CGST/SGST routing.
    - CGST + SGST applies for intra-state; IGST applies for inter-state (B2B).
    - `customer_gstin`: populated for GST-registered business customers.
    - `tyohaar_gstin`: the Tyohaar entity's GST number for the supply jurisdiction.

    Credit note support (future-ready):
    - `is_credit_note=True` marks this as a credit note.
    - `original_invoice_id` points to the invoice being reversed.
    - Credit notes carry negative line_items and negative totals.

    Billing snapshot (`billing_snapshot` JSONB):
    Captures customer details at invoice generation time so the invoice remains
    legally valid even if the customer later changes their details:
        {
          "name": "Priya Sharma",
          "email": "priya@example.com",
          "phone": "+919876543210",
          "address": "42, MG Road, Bengaluru - 560001, KA",
          "gstin": "29AABCU9603R1ZX",
          "pan": "AABCU9603R"
        }

    `line_items` JSONB (array):
        [
          {
            "description": "Tyohaar Gold Membership - Monthly",
            "quantity": 1,
            "unit_price": 999.00,
            "amount": 999.00,
            "hsn_sac_code": "997212"
          }
        ]
    """

    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        Index("ix_invoices_entity", "entity_type", "entity_id"),
        Index("ix_invoices_customer_id", "customer_id"),
        Index("ix_invoices_payment_id", "payment_id"),
        Index("ix_invoices_invoice_status", "invoice_status"),
        Index("ix_invoices_invoice_date", "invoice_date"),
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_non_negative"),
        CheckConstraint("tax_amount >= 0", name="ck_invoices_tax_non_negative"),
        CheckConstraint("total_amount >= 0", name="ck_invoices_total_non_negative"),
        CheckConstraint("discount_amount >= 0", name="ck_invoices_discount_non_negative"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    invoice_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Globally unique GST-compliant number e.g. INV-2024-MEM-001234.",
    )

    entity_type: Mapped[InvoiceEntityType] = mapped_column(
        SAEnum(InvoiceEntityType, name="invoice_entity_type", native_enum=False),
        nullable=False,
        comment="The platform domain that triggered this invoice.",
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the triggering entity (e.g., user_memberships.id for MEMBERSHIP). "
            "Not a FK to allow cross-domain flexibility."
        ),
    )

    # ── Parties ───────────────────────────────────────────────────────────────

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer or user this invoice is addressed to.",
    )

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        comment="The payment that settled this invoice, if applicable.",
    )

    # ── Status & Dates ────────────────────────────────────────────────────────

    invoice_status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status", native_enum=False),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )

    invoice_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of supply / invoice date printed on the document.",
    )

    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Payment due date. NULL for immediately-settled invoices.",
    )

    # ── Billing Snapshot ──────────────────────────────────────────────────────

    billing_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Customer billing details captured at invoice generation time. "
            "Immutable after issuance. Fields: name, email, phone, address, gstin, pan."
        ),
    )

    customer_gstin: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="Customer's GST registration number for B2B invoices.",
    )

    tyohaar_gstin: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="Tyohaar's GST number for the supply jurisdiction of this invoice.",
    )

    place_of_supply: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        comment="2-letter Indian state code (e.g., 'MH', 'KA') for GST routing.",
    )

    # ── Line Items ────────────────────────────────────────────────────────────

    line_items: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Array of billing line items: "
            "[{description, quantity, unit_price, amount, hsn_sac_code}]. "
            "Captured at generation time and immutable after ISSUED status."
        ),
    )

    # ── Financials ────────────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sum of line item amounts before discounts and taxes.",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="subtotal − discount_amount. Tax is calculated on this.",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total GST collected (CGST + SGST or IGST).",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="taxable_amount + tax_amount. The amount invoiced to the customer.",
    )

    # ── Tax Breakdown ─────────────────────────────────────────────────────────

    tax_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "GST component breakdown: "
            "{cgst_pct, cgst_amount, sgst_pct, sgst_amount, igst_pct, igst_amount, total_tax}. "
            "Populated on invoice generation; immutable after ISSUED."
        ),
    )

    # ── Credit Note ───────────────────────────────────────────────────────────

    is_credit_note: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when this document reverses or partially reverses a prior invoice.",
    )

    original_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=True,
        comment="For credit notes: the original invoice being reversed.",
    )

    # ── Lifecycle Timestamps ──────────────────────────────────────────────────

    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invoice transitioned from DRAFT to ISSUED.",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invoice was fully settled.",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason provided when cancelling or voiding the invoice.",
    )

    # ── Document ──────────────────────────────────────────────────────────────

    invoice_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="CDN URL of the generated PDF invoice document.",
    )

    issued_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin or system actor who issued this invoice.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped[User] = relationship(
        "User",
        foreign_keys=[customer_id],
        lazy="noload",
    )

    payment: Mapped[Payment | None] = relationship(
        "Payment",
        lazy="noload",
    )

    issued_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[issued_by_id],
        lazy="noload",
    )

    original_invoice: Mapped[Invoice | None] = relationship(
        "Invoice",
        remote_side="Invoice.id",
        foreign_keys=[original_invoice_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice id={self.id} number={self.invoice_number!r} "
            f"type={self.entity_type} total={self.total_amount} status={self.invoice_status}>"
        )
