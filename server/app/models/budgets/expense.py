"""
Expense — a single line item within a celebration budget plan.

Expenses are the atomic unit of budget tracking.  Every cost associated with
a celebration — whether entered manually by the customer, auto-created from a
Booking confirmation, or derived from a vendor assignment — produces one
Expense row.

An Expense belongs to a Budget (via budget_id) and optionally to a specific
category.  Multiple fields are nullable because an expense may start as a rough
estimate and progressively gain detail as the celebration is planned:

    Lifecycle example:
        1. Customer adds "Photography" with estimated_amount = ₹20,000
        2. Customer confirms package → Booking created → expense_source = BOOKING,
           planned_amount = ₹18,500 auto-filled from package pricing
        3. Payment captured → expense_source updated to PAYMENT,
           actual_amount = ₹18,500, is_paid = True

The three amount columns cover the three financial phases:
    estimated_amount — rough guess at planning time
    planned_amount   — budgeted amount after vendor/package selection
    actual_amount    — final confirmed or paid amount

All three are independent so historical planning data is never lost.

Recurring expenses (is_recurring = True) represent costs that repeat over a
time window, such as tent hire charged per day.  The service layer expands
recurrences into individual projected Expense rows for total cost calculation.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, ExpenseSource, ExpenseType
from app.models.mixins import (
    MetadataMixin,
    NotesMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.budgets.budget import Budget
    from app.models.budgets.category import ExpenseCategory
    from app.models.occasions.celebration import Celebration
    from app.models.vendors.vendor import Vendor
    from app.models.bookings.booking import Booking
    from app.models.payments.payment import Payment
    from app.models.packages.package import Package


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, MetadataMixin, Base):
    """
    A single line item in a celebration budget plan.

    Financial field semantics (all Numeric(12, 2), in `currency`):
    - `estimated_amount`: rough cost entered at planning time; never overwritten.
    - `planned_amount`:   confirmed budgeted cost after vendor/package selection.
    - `actual_amount`:    final paid/captured amount; set when is_paid becomes True.

    Source tracking:
    - MANUAL:               customer typed the expense directly.
    - BOOKING:              auto-created when Booking.status → CONFIRMED.
    - PAYMENT:              actual_amount auto-filled when Payment is captured.
    - VENDOR_ALLOCATION:    derived from a BookingAssignment for a specific vendor.
    - PACKAGE_ALLOCATION:   derived from PackagePricing at booking time.

    Polymorphic references (all nullable, SET NULL on target delete):
    - `vendor_id`   → pin this expense to a specific vendor.
    - `booking_id`  → link to the Booking that generated this expense.
    - `payment_id`  → link to the Payment that confirmed this expense.
    - `package_id`  → link to the Package whose pricing seeded this expense.

    Recurring:
    - `is_recurring = True` enables recurrence fields.
    - `recurrence_interval_days` defines the period (1 = daily, 7 = weekly).
    - The service layer creates sibling Expense rows for each occurrence
      between the due_date and recurrence_end_date.
    """

    __tablename__ = "expenses"

    __table_args__ = (
        Index("ix_expenses_celebration_id", "celebration_id"),
        Index("ix_expenses_budget_id", "budget_id"),
        Index("ix_expenses_category_id", "category_id"),
        Index("ix_expenses_expense_type", "expense_type"),
        Index("ix_expenses_expense_source", "expense_source"),
        Index("ix_expenses_vendor_id", "vendor_id"),
        Index("ix_expenses_booking_id", "booking_id"),
        Index("ix_expenses_payment_id", "payment_id"),
        Index("ix_expenses_celebration_type", "celebration_id", "expense_type"),
        Index("ix_expenses_celebration_paid", "celebration_id", "is_paid"),
        Index("ix_expenses_due_date", "due_date"),
        CheckConstraint(
            "estimated_amount IS NULL OR estimated_amount >= 0",
            name="ck_expenses_estimated_amount_non_negative",
        ),
        CheckConstraint(
            "planned_amount IS NULL OR planned_amount >= 0",
            name="ck_expenses_planned_amount_non_negative",
        ),
        CheckConstraint(
            "actual_amount IS NULL OR actual_amount >= 0",
            name="ck_expenses_actual_amount_non_negative",
        ),
        CheckConstraint(
            "recurrence_interval_days IS NULL OR recurrence_interval_days > 0",
            name="ck_expenses_recurrence_interval_positive",
        ),
        CheckConstraint(
            "NOT (is_recurring = true AND recurrence_interval_days IS NULL)",
            name="ck_expenses_recurring_requires_interval",
        ),
        CheckConstraint(
            "recurrence_end_date IS NULL OR due_date IS NULL OR recurrence_end_date >= due_date",
            name="ck_expenses_recurrence_end_after_due",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The celebration this expense belongs to",
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        comment="The budget plan this expense is tracked against",
    )

    # ── Classification ────────────────────────────────────────────────────────

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Category for this expense. SET NULL when category is removed.",
    )

    expense_type: Mapped[ExpenseType] = mapped_column(
        SAEnum(ExpenseType, name="expense_type", native_enum=False),
        nullable=False,
        default=ExpenseType.PLANNED,
        comment="Planning phase this expense belongs to",
    )

    expense_source: Mapped[ExpenseSource] = mapped_column(
        SAEnum(ExpenseSource, name="expense_source", native_enum=False),
        nullable=False,
        default=ExpenseSource.MANUAL,
        comment="Whether the expense was entered manually or auto-created by the platform",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment=(
            "Short human-readable description e.g. 'Photography', "
            "'Venue Deposit', 'Floral Arrangements'"
        ),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional details, vendor notes, or scope of work",
    )

    # ── Amounts ───────────────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
        comment="Currency denomination for all three amount fields",
    )

    estimated_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Rough cost estimate at the time the expense was first added. "
            "Never overwritten once set — preserves original planning data."
        ),
    )

    planned_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Confirmed budgeted amount after vendor or package selection. "
            "Auto-filled from package pricing on BOOKING source expenses."
        ),
    )

    actual_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Final confirmed or captured amount. "
            "Auto-filled from Payment on PAYMENT source expenses."
        ),
    )

    # ── Source Links (polymorphic references) ─────────────────────────────────

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        comment="Vendor whose services this expense covers",
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        comment="Booking that auto-generated this expense (expense_source = BOOKING)",
    )

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Payment whose capture confirmed the actual_amount "
            "(expense_source = PAYMENT)"
        ),
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Package whose pricing seeded the planned_amount for this expense",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date by which this expense is expected to be paid",
    )

    paid_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date on which the expense was actually paid; set when is_paid → True",
    )

    # ── Recurring ─────────────────────────────────────────────────────────────

    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for expenses that repeat at a fixed interval (e.g. daily tent hire)",
    )

    recurrence_interval_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Recurrence frequency in days (1 = daily, 7 = weekly). "
            "Required when is_recurring = True."
        ),
    )

    recurrence_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Last date up to which recurrence is active. Must be >= due_date.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when actual_amount is final and cannot be changed. "
            "Set when the associated payment is captured."
        ),
    )

    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the expense has been fully paid (cash is out)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        lazy="noload",
    )

    budget: Mapped[Budget] = relationship(
        "Budget",
        back_populates="expenses",
        lazy="noload",
    )

    category: Mapped[ExpenseCategory | None] = relationship(
        "ExpenseCategory",
        back_populates="expenses",
        lazy="noload",
    )

    vendor: Mapped[Vendor | None] = relationship(
        "Vendor",
        lazy="noload",
    )

    booking: Mapped[Booking | None] = relationship(
        "Booking",
        lazy="noload",
    )

    payment: Mapped[Payment | None] = relationship(
        "Payment",
        lazy="noload",
    )

    package: Mapped[Package | None] = relationship(
        "Package",
        lazy="noload",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def effective_amount(self) -> Decimal | None:
        """
        Best available amount in priority order:
        actual_amount → planned_amount → estimated_amount.

        Uses explicit None checks rather than truthiness to correctly
        handle zero-value amounts (Decimal('0.00') is falsy in Python).
        """
        if self.actual_amount is not None:
            return self.actual_amount
        if self.planned_amount is not None:
            return self.planned_amount
        return self.estimated_amount

    def __repr__(self) -> str:
        return (
            f"<Expense id={self.id} title={self.title!r} "
            f"type={self.expense_type} source={self.expense_source} "
            f"actual={self.actual_amount} paid={self.is_paid}>"
        )
