"""Budgets domain — service-layer exceptions."""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class BudgetNotFoundError(NotFoundError):
    def __init__(self, budget_id: str | None = None) -> None:
        super().__init__("Budget", budget_id)


class BudgetOwnershipError(PermissionError):
    default_message = "You do not own this budget."


class BudgetLimitError(BusinessRuleError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"You have reached the maximum of {limit} budgets.")


class ExpenseNotFoundError(NotFoundError):
    def __init__(self, expense_id: str | None = None) -> None:
        super().__init__("BudgetExpense", expense_id)


class ExpenseLimitError(BusinessRuleError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Budget has reached the maximum of {limit} expenses.")


class BudgetCategoryNotFoundError(NotFoundError):
    def __init__(self, category_id: str | None = None) -> None:
        super().__init__("BudgetCategory", category_id)


class CategoryInUseError(ConflictError):
    default_message = "This category is still referenced by existing expenses and cannot be deleted."


class BudgetAlertNotFoundError(NotFoundError):
    def __init__(self, alert_id: str | None = None) -> None:
        super().__init__("BudgetAlert", alert_id)


class InvalidExpenseAmountError(ValidationError):
    def __init__(self, min_amount: str, max_amount: str) -> None:
        super().__init__(
            f"Expense amount must be between {min_amount} and {max_amount}.",
            field="amount",
        )
