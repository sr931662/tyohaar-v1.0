"""
Budget — comprehensive financial plan for a customer's celebration.

A Budget is the full-featured financial tracker for a celebration.  It
coexists with the lightweight `CelebrationBudget` summary record in the
occasions domain, which the service layer keeps in sync as a fast-read cache
for home-screen progress indicators.

Design rationale — why both models exist:
- `CelebrationBudget` (occasions):   1:1 per celebration, written by the
  service layer for fast cached reads (planned / actual / remaining).
- `Budget` (budgets domain, this model): the authoritative, versioned plan
  that powers the full budget planning UX — alert thresholds, per-category
  allocations, version history, health computation, and expense relationships.

Only ONE Budget per celebration can have `budget_status = ACTIVE` at a time
(enforced via partial unique index).  Multiple Budget rows per celebration are
allowed to support "what-if" scenario planning (e.g. a customer drafts a
revised budget before activating it).

Financial field semantics (all Numeric(12, 2), in `currency`):
- `estimated_total`:  customer's initial rough estimate of the full spend.
- `planned_total`:    sum of all planned_amount values across Expense rows;
                      maintained by the service layer via SUM aggregation.
- `committed_total`:  sum of confirmed/captured booking amounts; represents
                      real payment obligations already in the system.
- `actual_total`:     sum of actual_amount from paid Expense rows; the
                      ground-truth total the customer has already spent.
- `remaining`:        planned_total − actual_total, cached for fast reads.

Alert system:
- When actual_total ≥ (alert_threshold_pct / 100) × planned_total,
  the service layer updates `health_status` and queues a notification.
- `alert_last_sent_at` prevents alert spam; next alert sent after a
  cooldown period defined in AppSettings.

`category_allocation` JSONB stores the customer's planned distribution:
    {
      "decoration":  {"planned": 15000.00, "allocated_pct": 20},
      "photography": {"planned": 25000.00, "allocated_pct": 33},
      "catering":    {"planned": 35000.00, "allocated_pct": 47}
    }

`version_history` is an append-only JSONB array capturing every time
`planned_total` is materially changed:
    [
      {"version": 1, "planned_total": 70000, "changed_at": "2024-03-01T10:00:00Z",
       "reason": "Initial plan"},
      {"version": 2, "planned_total": 80000, "changed_at": "2024-03-15T14:30:00Z",
       "reason": "Added entertainment budget"}
    ]
"""

from __future__ import annotations

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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    BudgetAlertLevel,
    BudgetHealthStatus,
    BudgetLifecycleStatus,
    Currency,
)
from app.models.mixins import (
    MetadataMixin,
    NotesMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration
    from app.models.users.user import User
    from app.models.budgets.expense import Expense


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, MetadataMixin, Base):
    """
    Comprehensive versioned financial plan for a customer's celebration.

    One celebration may have multiple Budget rows but only ONE active at a time.
    The service layer activates a budget via budget_status = ACTIVE and updates
    financial totals whenever Expense records change.

    Partial unique index ensures at most one ACTIVE budget per celebration:
        ix_budgets_unique_active_per_celebration
        WHERE budget_status = 'active' AND deleted_at IS NULL

    The budget is linked to all its individual Expense line items via the
    `expenses` relationship.  Aggregate totals are cached on this row so
    list-view queries never need to SUM across expenses.

    Alert flow:
        1. Expense updated → service recomputes actual_total.
        2. Compute utilization = actual_total / planned_total * 100.
        3. Determine new health_status and alert_level.
        4. If alert_level changed AND is_alert_enabled:
               send notification, set alert_last_sent_at = now().
    """

    __tablename__ = "budgets"

    __table_args__ = (
        # At most one ACTIVE (non-deleted) budget per celebration
        Index(
            "ix_budgets_unique_active_per_celebration",
            "celebration_id",
            unique=True,
            postgresql_where=text(
                "budget_status = 'active' AND deleted_at IS NULL"
            ),
        ),
        Index("ix_budgets_celebration_id", "celebration_id"),
        Index("ix_budgets_customer_id", "customer_id"),
        Index("ix_budgets_budget_status", "budget_status"),
        Index("ix_budgets_customer_status", "customer_id", "budget_status"),
        Index("ix_budgets_health_status", "health_status"),
        CheckConstraint("estimated_total >= 0", name="ck_budgets_estimated_total_non_negative"),
        CheckConstraint("planned_total >= 0", name="ck_budgets_planned_total_non_negative"),
        CheckConstraint("committed_total >= 0", name="ck_budgets_committed_total_non_negative"),
        CheckConstraint("actual_total >= 0", name="ck_budgets_actual_total_non_negative"),
        CheckConstraint(
            "alert_threshold_pct BETWEEN 1 AND 100",
            name="ck_budgets_alert_threshold_pct_range",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The celebration this budget plan is for",
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "Denormalized from Celebration for direct customer-scoped queries "
            "without joining through celebrations."
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        default="My Budget",
        comment="Customer-defined label e.g. 'Birthday Budget 2024', 'Revised Plan'",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional notes on what this budget plan covers or its revision rationale",
    )

    # ── Financial Totals ──────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
        comment="All monetary fields are denominated in this currency",
    )

    estimated_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Customer's rough overall estimate entered at the start of planning",
    )

    planned_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment=(
            "Cached sum of Expense.planned_amount for all non-deleted expenses. "
            "Maintained by the service layer; drives utilization calculations."
        ),
    )

    committed_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment=(
            "Sum of confirmed Booking totals linked to this celebration. "
            "Represents real payment obligations already made."
        ),
    )

    actual_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment=(
            "Cached sum of Expense.actual_amount for paid expenses. "
            "Ground-truth total spend; drives health_status computation."
        ),
    )

    remaining: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="planned_total − actual_total. Cached; updated on every expense change.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    budget_status: Mapped[BudgetLifecycleStatus] = mapped_column(
        SAEnum(BudgetLifecycleStatus, name="budget_lifecycle_status", native_enum=False),
        nullable=False,
        default=BudgetLifecycleStatus.DRAFT,
        comment="Operational phase of this budget plan",
    )

    health_status: Mapped[BudgetHealthStatus] = mapped_column(
        SAEnum(BudgetHealthStatus, name="budget_health_status", native_enum=False),
        nullable=False,
        default=BudgetHealthStatus.ON_TRACK,
        comment="Real-time comparison of actual vs planned spend; recomputed on expense changes",
    )

    # ── Alert Configuration ───────────────────────────────────────────────────

    alert_threshold_pct: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=80,
        comment=(
            "Notify the customer when actual_total reaches this percentage of planned_total. "
            "Must be between 1 and 100. Default 80 (alert at 80% utilisation)."
        ),
    )

    is_alert_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False disables budget threshold alerts for this plan",
    )

    alert_level: Mapped[BudgetAlertLevel | None] = mapped_column(
        SAEnum(BudgetAlertLevel, name="budget_alert_level", native_enum=False),
        nullable=True,
        comment="Current alert severity; updated whenever actual_total changes",
    )

    alert_last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Timestamp of the most recent alert notification sent. "
            "Used to enforce a cooldown period between repeat alerts."
        ),
    )

    # ── Analytics & Allocation ────────────────────────────────────────────────

    category_allocation: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Customer-set spending plan per category (keyed by BudgetCategory slug). "
            'Structure: {"decoration": {"planned": 15000.00, "allocated_pct": 20}, ...}'
        ),
    )

    version_history: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Append-only array capturing every material change to planned_total. "
            "Structure: [{version, planned_total, changed_at (ISO-8601), reason}]"
        ),
    )

    # ── Version ───────────────────────────────────────────────────────────────

    revision_number: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment=(
            "Monotonically increasing counter incremented whenever the customer "
            "materially revises the plan. Correlates with version_history entries."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        lazy="noload",
    )

    customer: Mapped[User] = relationship(
        "User",
        lazy="noload",
    )

    expenses: Mapped[list[Expense]] = relationship(
        "Expense",
        back_populates="budget",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def utilization_pct(self) -> float:
        """
        Percentage of the planned budget already spent.

        Returns 0.0 when planned_total is zero to avoid division by zero.
        Used by the service layer to determine health_status and alert_level.
        """
        if not self.planned_total:
            return 0.0
        return float(self.actual_total / self.planned_total * 100)

    @property
    def is_over_budget(self) -> bool:
        """True when actual spending exceeds the planned total."""
        return self.actual_total > self.planned_total and self.planned_total > 0

    def __repr__(self) -> str:
        return (
            f"<Budget id={self.id} name={self.name!r} "
            f"status={self.budget_status} health={self.health_status} "
            f"planned={self.planned_total} actual={self.actual_total}>"
        )
