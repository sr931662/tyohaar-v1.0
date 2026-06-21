"""
Budgets domain — create (request body) schemas.

Used by POST endpoints to create Budget and BudgetExpense records.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.schemas.budgets.common import (
    BudgetCategory,
    Currency,
    ExpenseSource,
    ExpenseType,
)


class BudgetCreate(BaseSchema):
    """
    Payload for creating a new budget for a celebration.

    One celebration may have at most one budget (UNIQUE constraint on
    celebration_id). The service layer computes contingency_amount from
    contingency_pct and total_planned before persisting.
    """

    celebration_id: uuid.UUID = Field(
        description="Celebration this budget belongs to (unique per celebration)"
    )
    user_id: uuid.UUID = Field(
        description="Owner of the budget (must match celebration owner)"
    )
    currency: Currency = Field(
        default=Currency.INR,
        description="Currency for all monetary values in this budget",
    )
    total_planned: MoneyAmount = Field(
        description="Customer's total planned spending limit"
    )
    contingency_pct: Decimal = Field(
        default=Decimal("10"),
        ge=Decimal("0"),
        le=Decimal("50"),
        decimal_places=2,
        description="Contingency buffer as a percentage of total_planned (0–50%)",
    )
    alert_threshold_pct: Decimal = Field(
        default=Decimal("80"),
        ge=Decimal("1"),
        le=Decimal("100"),
        decimal_places=2,
        description="Spending percentage at which alerts are triggered (1–100%)",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Free-form notes about the budget plan",
    )

    @field_validator("total_planned")
    @classmethod
    def planned_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("total_planned must be greater than zero")
        return v


class BudgetExpenseCreate(BaseSchema):
    """
    Payload for adding an expense entry to a budget.

    The service layer updates budget aggregates (total_spent,
    total_estimated, health_status) after each expense is created.
    """

    budget_id: uuid.UUID = Field(description="Parent budget this expense belongs to")
    category: BudgetCategory = Field(description="Expense category")
    title: str = Field(
        min_length=1,
        max_length=300,
        description="Short label for this expense (e.g. 'DJ setup', 'Photographer')",
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional detailed description",
    )
    amount: MoneyAmount = Field(description="Expense amount in the budget's currency")
    expense_type: ExpenseType = Field(
        default=ExpenseType.PLANNED,
        description="Nature of this expense in the planning lifecycle",
    )
    expense_source: ExpenseSource = Field(
        default=ExpenseSource.MANUAL,
        description="How this expense record was created",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="Linked booking or payment ID when source is BOOKING or PAYMENT",
    )
    expense_date: date | None = Field(
        default=None,
        description="Date on which this expense was or will be incurred",
    )
    vendor_name: str | None = Field(
        default=None,
        max_length=200,
        description="Name of the vendor for this expense",
    )
    is_paid: bool = Field(
        default=False,
        description="Whether this expense has been paid",
    )
    receipt_url: str | None = Field(
        default=None,
        max_length=2048,
        description="URL of the uploaded receipt or invoice",
    )


class BudgetCategoryCreate(BaseSchema):
    """Admin: create a CMS-managed budget category definition."""

    name: str = Field(min_length=2, max_length=100, description="Display name for this category")
    slug: str = Field(min_length=2, max_length=100, description="URL-safe unique identifier")
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=100, description="Icon name or URL")
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class BudgetAlertCreate(BaseSchema):
    """Create a spending alert rule for a budget."""

    budget_id: uuid.UUID = Field(description="Budget this alert belongs to")
    threshold_pct: Decimal = Field(
        ge=Decimal("1"), le=Decimal("100"), decimal_places=2,
        description="Spending percentage that triggers this alert",
    )
    alert_level: str = Field(
        default="warning",
        description="Severity level: 'info', 'warning', or 'critical'",
    )
    message: str | None = Field(default=None, max_length=500)
