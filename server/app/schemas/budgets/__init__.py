"""
Budgets domain schema package.

Single stable import entry point:

    from app.schemas.budgets import BudgetCreate, BudgetResponse, BudgetPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
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

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.budgets.create import (
    BudgetCreate,
    BudgetExpenseCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.budgets.update import (
    BudgetExpenseUpdate,
    BudgetUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.budgets.response import (
    BudgetCategoryDefinitionResponse,
    BudgetDetailResponse,
    BudgetExpenseResponse,
    BudgetResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.budgets.filters import (
    BudgetExpenseFilters,
    BudgetFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.budgets.pagination import (
    BudgetExpensePage,
    BudgetPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.budgets.internal import (
    BudgetHealthUpdate,
    BudgetInternal,
)

__all__ = [
    # common / enums
    "BudgetCategory",
    "BudgetLifecycleStatus",
    "BudgetHealthStatus",
    "BudgetAlertLevel",
    "ExpenseType",
    "ExpenseSource",
    "Currency",
    "BudgetSummarySchema",
    # create
    "BudgetCreate",
    "BudgetExpenseCreate",
    # update
    "BudgetUpdate",
    "BudgetExpenseUpdate",
    # response
    "BudgetResponse",
    "BudgetExpenseResponse",
    "BudgetCategoryDefinitionResponse",
    "BudgetDetailResponse",
    # filters
    "BudgetFilters",
    "BudgetExpenseFilters",
    # pagination
    "BudgetPage",
    "BudgetExpensePage",
    # internal
    "BudgetInternal",
    "BudgetHealthUpdate",
]
