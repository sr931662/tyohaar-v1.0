"""
Budgets domain — public API response schemas.

Security contract:
  - deleted_at is NEVER included in any response schema.
  - Internal service fields (recomputed health scores) are read-only.

Naming note:
  BudgetCategory is the *enum* from app.models.enums.
  BudgetCategoryDefinitionResponse represents the separate *model*
  (app.models.budgets.category) for CMS-managed category metadata.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import IDSchema, MoneyAmount
from app.schemas.budgets.common import (
    BudgetAlertLevel,
    BudgetCategory,
    BudgetHealthStatus,
    BudgetLifecycleStatus,
    BudgetSummarySchema,
    Currency,
    ExpenseSource,
    ExpenseType,
)


class BudgetExpenseResponse(IDSchema):
    """
    Public-safe representation of a single BudgetExpense entry.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    budget_id: uuid.UUID = Field(description="Parent budget")
    category: BudgetCategory = Field(description="Expense category")
    title: str = Field(description="Expense label")
    description: str | None = Field(default=None, description="Optional detail")
    amount: MoneyAmount = Field(description="Expense amount")
    expense_type: ExpenseType = Field(description="Nature of expense in planning lifecycle")
    expense_source: ExpenseSource = Field(description="How this expense was created")
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="Linked booking or payment ID",
    )
    expense_date: date | None = Field(
        default=None,
        description="Date the expense was or will be incurred",
    )
    vendor_name: str | None = Field(default=None, description="Vendor for this expense")
    is_paid: bool = Field(description="Whether this expense has been paid")
    paid_at: datetime | None = Field(default=None, description="When payment was made")
    receipt_url: str | None = Field(default=None, description="URL of uploaded receipt")
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class BudgetResponse(IDSchema):
    """
    Public-safe representation of a Budget.

    Includes aggregated totals and health indicators. deleted_at is excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    celebration_id: uuid.UUID = Field(description="Associated celebration")
    user_id: uuid.UUID = Field(description="Budget owner")
    currency: Currency = Field(description="Budget currency")
    total_planned: MoneyAmount = Field(description="Customer's stated spending limit")
    total_spent: MoneyAmount = Field(description="Sum of actual expenses")
    total_estimated: MoneyAmount = Field(description="Sum of estimated expenses")
    contingency_pct: Decimal = Field(description="Contingency buffer percentage")
    contingency_amount: MoneyAmount = Field(
        description="Contingency buffer amount (contingency_pct / 100 × total_planned)"
    )
    lifecycle_status: BudgetLifecycleStatus = Field(description="Budget operational phase")
    health_status: BudgetHealthStatus = Field(
        description="Real-time spending health indicator"
    )
    alert_threshold_pct: Decimal = Field(
        description="Spending % at which budget alerts trigger"
    )
    alert_level: BudgetAlertLevel | None = Field(
        default=None,
        description="Current alert severity; null when no alert is active",
    )
    notes: str | None = Field(default=None, description="User's budget notes")
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class BudgetCategoryDefinitionResponse(IDSchema):
    """
    CMS-managed budget category definition.

    Represents a row from the budget_categories table (the BudgetCategory
    *model*, not the BudgetCategory enum). Used for category picker UIs.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(description="Display name (e.g. 'Decoration')")
    slug: str = Field(description="URL-safe slug (e.g. 'decoration')")
    category: BudgetCategory = Field(
        description="Corresponding BudgetCategory enum value"
    )
    icon_url: str | None = Field(
        default=None,
        description="URL of the category icon asset",
    )
    description: str | None = Field(
        default=None,
        description="Short description shown in the category picker",
    )
    is_active: bool = Field(description="Whether this category is available to users")
    display_order: int = Field(description="Ascending sort order for display")


class BudgetDetailResponse(BudgetResponse):
    """
    Extended budget view including expense breakdown.

    Returned by GET /budgets/{id}?detail=true. Includes all expense
    entries and a per-category spending breakdown for chart rendering.
    """

    expenses: list[BudgetExpenseResponse] = Field(
        default_factory=list,
        description="All expense entries for this budget",
    )
    category_breakdown: dict[str, Decimal] = Field(
        default_factory=dict,
        description=(
            "Keyed by BudgetCategory value; value is total amount spent "
            "in that category. Used for pie/bar chart rendering."
        ),
    )


# Alias consumed by the budgets controller
BudgetCategoryResponse = BudgetCategoryDefinitionResponse
