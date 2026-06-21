"""Budgets domain — async validator helpers that operate inside a UnitOfWork."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.models.budgets.budget import Budget
from app.models.budgets.category import ExpenseCategory
from app.models.budgets.expense import Expense
from app.repositories.unit_of_work import UnitOfWork
from app.services.budgets.constants import (
    MAX_BUDGETS_PER_USER,
    MAX_EXPENSE_AMOUNT,
    MIN_EXPENSE_AMOUNT,
)
from app.services.budgets.exceptions import (
    BudgetCategoryNotFoundError,
    BudgetLimitError,
    BudgetNotFoundError,
    BudgetOwnershipError,
    ExpenseNotFoundError,
    InvalidExpenseAmountError,
)


async def validate_budget_exists(
    budget_id: uuid.UUID,
    uow: UnitOfWork,
) -> Budget:
    """Fetch a budget by ID or raise BudgetNotFoundError."""
    budget = await uow.budgets.budgets.get_by_id(budget_id)
    if budget is None:
        raise BudgetNotFoundError(str(budget_id))
    return budget


async def validate_budget_ownership(
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> Budget:
    """Fetch budget and verify customer_id matches or raise BudgetOwnershipError."""
    budget = await validate_budget_exists(budget_id, uow)
    if budget.customer_id != user_id:
        raise BudgetOwnershipError()
    return budget


async def validate_budget_limit(
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    """Raise BudgetLimitError when the user has reached MAX_BUDGETS_PER_USER."""
    count = await uow.budgets.budgets.count(
        uow.budgets.budgets._model.customer_id == user_id,  # type: ignore[attr-defined]
    )
    if count >= MAX_BUDGETS_PER_USER:
        raise BudgetLimitError(MAX_BUDGETS_PER_USER)


async def validate_expense_ownership(
    expense_id: uuid.UUID,
    budget_id: uuid.UUID,
    uow: UnitOfWork,
) -> Expense:
    """Fetch expense and verify it belongs to budget_id or raise ExpenseNotFoundError."""
    expense = await uow.budgets.expenses.get_by_id(expense_id)
    if expense is None or expense.budget_id != budget_id:
        raise ExpenseNotFoundError(str(expense_id))
    return expense


def validate_expense_amount(amount: Decimal) -> None:
    """Raise InvalidExpenseAmountError when amount is out of bounds."""
    if amount < MIN_EXPENSE_AMOUNT or amount > MAX_EXPENSE_AMOUNT:
        raise InvalidExpenseAmountError(str(MIN_EXPENSE_AMOUNT), str(MAX_EXPENSE_AMOUNT))


async def validate_category_exists(
    category_id: uuid.UUID,
    uow: UnitOfWork,
) -> ExpenseCategory:
    """Fetch an ExpenseCategory by ID or raise BudgetCategoryNotFoundError."""
    category = await uow.budgets.categories.get_by_id(category_id)
    if category is None:
        raise BudgetCategoryNotFoundError(str(category_id))
    return category
