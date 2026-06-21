"""Budgets domain — service-layer constants."""

from __future__ import annotations

from decimal import Decimal

MAX_BUDGETS_PER_USER = 20
MAX_EXPENSES_PER_BUDGET = 500
MAX_BUDGET_CATEGORIES = 50          # global system categories
MAX_BUDGET_AMOUNT = Decimal("100000000.00")
MIN_BUDGET_AMOUNT = Decimal("0.00")
MIN_EXPENSE_AMOUNT = Decimal("1.00")
MAX_EXPENSE_AMOUNT = Decimal("100000000.00")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

ALERT_THRESHOLD_WARN = 0.5     # 50% utilisation
ALERT_THRESHOLD_CRITICAL = 0.8  # 80% utilisation
ALERT_THRESHOLD_OVER = 1.0      # 100% utilisation
