"""
Budgets domain — query filter schemas.

Used as query-parameter models on list endpoints. All fields are optional;
absent fields are ignored by the repository layer.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.budgets.common import (
    BudgetCategory,
    BudgetHealthStatus,
    BudgetLifecycleStatus,
    Currency,
    ExpenseSource,
    ExpenseType,
)


class BudgetFilters(BaseSchema):
    """
    Filter parameters for the budget list endpoint.

    GET /budgets?user_id=...&lifecycle_status=active
    """

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter budgets owned by this user",
    )
    celebration_id: uuid.UUID | None = Field(
        default=None,
        description="Filter budgets for a specific celebration",
    )
    lifecycle_status: BudgetLifecycleStatus | None = Field(
        default=None,
        description="Filter by budget lifecycle phase",
    )
    health_status: BudgetHealthStatus | None = Field(
        default=None,
        description="Filter by spending health indicator",
    )
    currency: Currency | None = Field(
        default=None,
        description="Filter budgets in a specific currency",
    )


class BudgetExpenseFilters(BaseSchema):
    """
    Filter parameters for the budget expense list endpoint.

    GET /budgets/{id}/expenses?category=catering&is_paid=false
    """

    budget_id: uuid.UUID | None = Field(
        default=None,
        description="Filter expenses belonging to this budget",
    )
    category: BudgetCategory | None = Field(
        default=None,
        description="Filter by expense category",
    )
    expense_type: ExpenseType | None = Field(
        default=None,
        description="Filter by expense nature (PLANNED, ACTUAL, etc.)",
    )
    expense_source: ExpenseSource | None = Field(
        default=None,
        description="Filter by how the expense was created",
    )
    is_paid: bool | None = Field(
        default=None,
        description="Filter paid or unpaid expenses",
    )
    from_date: date | None = Field(
        default=None,
        description="Inclusive start of expense_date range",
    )
    to_date: date | None = Field(
        default=None,
        description="Inclusive end of expense_date range",
    )
