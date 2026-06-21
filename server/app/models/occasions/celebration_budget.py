"""
CelebrationBudget — planned vs actual budget summary for a celebration.

One budget record per celebration (1:1 enforced via UNIQUE constraint).
"""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration


class BudgetStatus(str, enum.Enum):
    """
    Budget health status relative to planned spending.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    ON_TRACK = "on_track"
    SLIGHTLY_OVER = "slightly_over"
    OVER_BUDGET = "over_budget"
    UNDER_BUDGET = "under_budget"


class CelebrationBudget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Budget tracker for a celebration — planned vs actual spending summary.

    1:1 relationship with Celebration (enforced via UNIQUE on celebration_id).

    `remaining` is cached (not computed on read) for fast home screen display.
    The service layer must update it whenever `actual_spent` changes.

    `category_breakdown` JSONB tracks per-category budget allocation:
        {
          "decoration":   {"planned": 15000, "actual": 14500},
          "photography":  {"planned": 20000, "actual": null},
          "catering":     {"planned": 30000, "actual": 28000},
          "cake":         {"planned": 3000,  "actual": 2800}
        }
    Keys correspond to BudgetCategory enum values from enums.py.
    """

    __tablename__ = "celebration_budgets"

    __table_args__ = (
        UniqueConstraint("celebration_id", name="uq_celebration_budgets_celebration_id"),
        CheckConstraint("planned_amount >= 0", name="ck_budget_planned_non_negative"),
        CheckConstraint("actual_spent >= 0", name="ck_budget_actual_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ── Amounts ───────────────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    planned_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total budget set by the customer at planning time",
    )

    actual_spent: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Sum of all confirmed booking amounts. Updated by service layer.",
    )

    remaining: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="planned_amount - actual_spent. Cached; updated by service layer.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    budget_status: Mapped[BudgetStatus] = mapped_column(
        SAEnum(BudgetStatus, name="budget_status", native_enum=False),
        nullable=False,
        default=BudgetStatus.ON_TRACK,
    )

    # ── Breakdown ─────────────────────────────────────────────────────────────

    category_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Per-category budget tracking keyed by BudgetCategory slug: "
            "{category_slug: {planned: float, actual: float | null}}"
        ),
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        back_populates="budget",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CelebrationBudget celebration_id={self.celebration_id} "
            f"planned={self.planned_amount} spent={self.actual_spent} "
            f"status={self.budget_status}>"
        )
