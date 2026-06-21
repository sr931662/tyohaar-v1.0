"""
Budgets domain — update (PATCH request body) schemas.

All fields are optional; only provided fields are applied. The service
layer recomputes derived fields (contingency_amount, health_status, etc.)
whenever the underlying values change.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.schemas.budgets.common import (
    BudgetCategory,
    BudgetLifecycleStatus,
    ExpenseType,
)


class BudgetUpdate(BaseSchema):
    """
    Partial update payload for a Budget.

    Changing total_planned or contingency_pct will trigger a service-layer
    recalculation of contingency_amount and a re-evaluation of health_status.
    """

    total_planned: MoneyAmount | None = Field(
        default=None,
        description="Revised total planned budget",
    )
    contingency_pct: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("50"),
        decimal_places=2,
        description="Updated contingency buffer percentage (0–50%)",
    )
    lifecycle_status: BudgetLifecycleStatus | None = Field(
        default=None,
        description="New lifecycle status (e.g. ACTIVE → PAUSED)",
    )
    alert_threshold_pct: Decimal | None = Field(
        default=None,
        ge=Decimal("1"),
        le=Decimal("100"),
        decimal_places=2,
        description="Updated alert trigger percentage",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated free-form notes",
    )


class BudgetExpenseUpdate(BaseSchema):
    """
    Partial update payload for a BudgetExpense.

    Changing amount or expense_type will trigger a service-layer
    recalculation of budget aggregate totals (total_spent / total_estimated).
    """

    category: BudgetCategory | None = Field(
        default=None,
        description="Updated expense category",
    )
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=300,
        description="Updated expense label",
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated description",
    )
    amount: MoneyAmount | None = Field(
        default=None,
        description="Revised expense amount",
    )
    expense_type: ExpenseType | None = Field(
        default=None,
        description="Updated expense type",
    )
    expense_date: date | None = Field(
        default=None,
        description="Updated expense date",
    )
    vendor_name: str | None = Field(
        default=None,
        max_length=200,
        description="Updated vendor name",
    )
    is_paid: bool | None = Field(
        default=None,
        description="Mark as paid or unpaid",
    )
    paid_at: datetime | None = Field(
        default=None,
        description="Timestamp when payment was made",
    )
    receipt_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Updated receipt URL",
    )


class BudgetCategoryUpdate(BaseSchema):
    """Admin: partial update for a CMS-managed budget category definition."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=100)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
