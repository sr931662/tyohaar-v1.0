"""Budgets domain — stateless helper functions."""

from __future__ import annotations

from decimal import Decimal


def calculate_total_spent(expenses: list[dict]) -> Decimal:
    """Sum the 'actual_amount' field across all expense dicts.

    Skips entries where actual_amount is None or missing.
    """
    total = Decimal("0.00")
    for expense in expenses:
        amount = expense.get("actual_amount") or expense.get("amount")
        if amount is not None:
            total += Decimal(str(amount))
    return total.quantize(Decimal("0.01"))


def calculate_remaining_budget(total: Decimal, spent: Decimal) -> Decimal:
    """Return total − spent (may be negative when over budget)."""
    return (total - spent).quantize(Decimal("0.01"))


def calculate_budget_utilization(spent: Decimal, total: Decimal) -> float:
    """Return a fraction in the range 0.0–∞ (>1.0 means over budget).

    Returns 0.0 when total is zero to avoid division by zero.
    """
    if not total:
        return 0.0
    return float(spent / total)


def is_budget_overrun(spent: Decimal, total: Decimal) -> bool:
    """Return True when actual spending exceeds the planned total."""
    return total > Decimal("0") and spent > total


def group_expenses_by_category(expenses: list[dict]) -> dict[str, Decimal]:
    """Aggregate expense amounts by category name/slug.

    Expects each dict to contain 'category' (string key) and
    'actual_amount' or 'amount' (Decimal-compatible value).
    """
    result: dict[str, Decimal] = {}
    for expense in expenses:
        category = str(expense.get("category") or "uncategorized")
        amount = expense.get("actual_amount") or expense.get("amount") or Decimal("0")
        result[category] = result.get(category, Decimal("0")) + Decimal(str(amount))
    return {k: v.quantize(Decimal("0.01")) for k, v in result.items()}
