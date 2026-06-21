"""
Budgets domain — shared types, enum re-exports, and nested schemas.

Import from here instead of importing enums directly in other budget
schema modules.

Naming note: BudgetCategory is an *enum* in app.models.enums.
The separate BudgetCategory *model* (app.models.budgets.category) is
for CMS-managed category definitions and is referenced in response.py
as BudgetCategoryDefinitionResponse to avoid naming conflicts.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, computed_field, model_validator

from app.models.enums import (
    BudgetAlertLevel,
    BudgetCategory,
    BudgetHealthStatus,
    BudgetLifecycleStatus,
    Currency,
    ExpenseSource,
    ExpenseType,
)
from app.schemas.base import BaseSchema, MoneyAmount


class BudgetSummarySchema(BaseSchema):
    """
    Computed financial summary for a budget.

    Returned as a convenience nested object in BudgetResponse and
    BudgetDetailResponse. The `remaining` field is computed client-side
    from the provided values but is also included here for convenience.
    """

    total_planned: MoneyAmount = Field(
        description="Customer's stated total planned budget"
    )
    total_spent: MoneyAmount = Field(
        description="Sum of all ACTUAL expense entries"
    )
    total_estimated: MoneyAmount = Field(
        description="Sum of all ESTIMATED expense entries"
    )
    contingency_amount: MoneyAmount = Field(
        description="Buffer amount derived from contingency_pct × total_planned"
    )
    remaining: Decimal = Field(
        description=(
            "Spendable amount left: total_planned + contingency_amount - total_spent. "
            "May be negative if over budget."
        )
    )


__all__ = [
    # nested schemas
    "BudgetSummarySchema",
    # re-exported enums
    "BudgetCategory",
    "BudgetLifecycleStatus",
    "BudgetHealthStatus",
    "BudgetAlertLevel",
    "ExpenseType",
    "ExpenseSource",
    "Currency",
]
