"""
Budgets domain — paginated list response schemas.

Both use keyset (cursor-based) pagination via CursorPage for O(1) performance
at scale. Pass next_cursor verbatim to the next request to advance pages.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.budgets.response import BudgetExpenseResponse, BudgetResponse

BudgetPage = CursorPage[BudgetResponse]
"""Paginated list of budget records."""

BudgetExpensePage = CursorPage[BudgetExpenseResponse]
"""Paginated list of budget expense records."""

__all__ = [
    "BudgetPage",
    "BudgetExpensePage",
]
