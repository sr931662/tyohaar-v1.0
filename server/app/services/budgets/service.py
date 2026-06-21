"""
BudgetService — budget CRUD, expense management, category admin, and alerts.

All public methods open their own UoW so each call is one atomic transaction.
Financial aggregates (planned_total, actual_total, remaining) are recomputed
after every expense mutation and written back to the Budget row in the same
transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.budgets.budget import Budget
from app.models.budgets.category import ExpenseCategory
from app.models.budgets.expense import Expense
from app.models.enums import BudgetLifecycleStatus, ExpenseSource, ExpenseType
from app.schemas.base import CursorPage
from app.schemas.budgets.create import BudgetCreate, BudgetExpenseCreate
from app.schemas.budgets.response import (
    BudgetCategoryDefinitionResponse,
    BudgetDetailResponse,
    BudgetExpenseResponse,
    BudgetResponse,
)
from app.services.base import BaseService
from app.services.budgets.constants import MAX_EXPENSES_PER_BUDGET
from app.services.budgets.exceptions import (
    BudgetAlertNotFoundError,
    BudgetCategoryNotFoundError,
    BudgetNotFoundError,
    CategoryInUseError,
    ExpenseLimitError,
)
from app.services.budgets.helpers import (
    calculate_budget_utilization,
    calculate_remaining_budget,
    calculate_total_spent,
    group_expenses_by_category,
    is_budget_overrun,
)
from app.services.budgets.validators import (
    validate_budget_exists,
    validate_budget_limit,
    validate_budget_ownership,
    validate_category_exists,
    validate_expense_amount,
    validate_expense_ownership,
)

# ---------------------------------------------------------------------------
# Inline response stubs for analytics shapes not yet in schema modules
# ---------------------------------------------------------------------------
from app.schemas.base import BaseSchema as _BaseSchema


class BudgetSummaryResponse(_BaseSchema):
    budget_id: UUID
    total_amount: Decimal
    total_spent: Decimal
    remaining: Decimal
    utilization_pct: float
    is_overrun: bool
    expenses_by_category: dict[str, Decimal]


class CategorySpendResponse(_BaseSchema):
    category: str
    amount: Decimal


class BudgetAlertResponse(_BaseSchema):
    budget_id: UUID
    threshold_pct: float
    message: str


def _wrap_cursor(items: list, limit: int) -> CursorPage:
    has_more = len(items) > limit
    return CursorPage(
        items=items[:limit] if has_more else items,
        has_more=has_more,
        next_cursor=None,
    )


async def _recompute_budget_totals(budget: Budget, uow) -> Budget:
    """Recompute and persist planned_total, actual_total, and remaining from
    the current set of non-deleted expense rows for this budget."""
    expenses = await uow.budgets.expenses.find_by_budget(budget.id, limit=10000)
    planned = sum(
        (e.planned_amount or Decimal("0") for e in expenses), Decimal("0")
    )
    actual = sum(
        (e.actual_amount or Decimal("0") for e in expenses), Decimal("0")
    )
    remaining = calculate_remaining_budget(planned, actual)
    return await uow.budgets.budgets.update(budget, {
        "planned_total": planned,
        "actual_total": actual,
        "remaining": remaining,
    })


class BudgetService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # =========================================================================
    # Budget CRUD
    # =========================================================================

    async def create_budget(
        self,
        user_id: UUID,
        data: BudgetCreate,
    ) -> BudgetResponse:
        """Create a new budget, enforcing the per-user limit."""
        async with self._uow() as uow:
            await validate_budget_limit(user_id, uow)

            budget = Budget(
                customer_id=user_id,
                celebration_id=data.celebration_id,
                estimated_total=data.total_planned,
                planned_total=data.total_planned,
                committed_total=Decimal("0.00"),
                actual_total=Decimal("0.00"),
                remaining=data.total_planned,
                currency=data.currency,
                alert_threshold_pct=int(data.alert_threshold_pct),
                budget_status=BudgetLifecycleStatus.DRAFT,
            )
            budget = await uow.budgets.budgets.create(budget)
            await uow.commit()
        return BudgetResponse.model_validate(budget)

    async def get_budget(
        self,
        budget_id: UUID,
        user_id: UUID,
    ) -> BudgetDetailResponse:
        """Return full budget detail including all expense rows and breakdown."""
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            expenses = await uow.budgets.expenses.find_by_budget(budget_id)

        expense_responses = [BudgetExpenseResponse.model_validate(e) for e in expenses]
        expense_dicts = [
            {
                "category": str(e.category_id) if e.category_id else "uncategorized",
                "actual_amount": e.actual_amount or Decimal("0"),
            }
            for e in expenses
        ]
        breakdown = group_expenses_by_category(expense_dicts)

        detail = BudgetDetailResponse.model_validate(budget)
        detail.expenses = expense_responses
        detail.category_breakdown = breakdown
        return detail

    async def list_budgets(
        self,
        user_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            budgets = await uow.budgets.budgets.find_by_customer(
                user_id, limit=limit + 1
            )
        responses = [BudgetResponse.model_validate(b) for b in budgets]
        return _wrap_cursor(responses, limit)

    async def update_budget(
        self,
        budget_id: UUID,
        user_id: UUID,
        data: object,  # BudgetUpdate schema
    ) -> BudgetResponse:
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            update_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            budget = await uow.budgets.budgets.update(budget, update_dict)
            await uow.commit()
        return BudgetResponse.model_validate(budget)

    async def delete_budget(self, budget_id: UUID, user_id: UUID) -> None:
        """Soft-delete the budget AND all its expenses in one transaction."""
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            # Soft-delete all child expenses
            expenses = await uow.budgets.expenses.find_by_budget(budget_id, limit=10000)
            for expense in expenses:
                await uow.budgets.expenses.soft_delete(expense)
            await uow.budgets.budgets.soft_delete(budget)
            await uow.commit()

    # =========================================================================
    # Budget analytics
    # =========================================================================

    async def get_budget_summary(
        self,
        budget_id: UUID,
        user_id: UUID,
    ) -> BudgetSummaryResponse:
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            expenses = await uow.budgets.expenses.find_by_budget(budget_id, limit=10000)

        expense_dicts = [
            {
                "category": str(e.category_id) if e.category_id else "uncategorized",
                "actual_amount": e.actual_amount or Decimal("0"),
                "amount": e.actual_amount or Decimal("0"),
            }
            for e in expenses
        ]
        total_spent = calculate_total_spent(expense_dicts)
        remaining = calculate_remaining_budget(budget.planned_total, total_spent)
        utilization = calculate_budget_utilization(total_spent, budget.planned_total)
        overrun = is_budget_overrun(total_spent, budget.planned_total)
        by_category = group_expenses_by_category(expense_dicts)

        return BudgetSummaryResponse(
            budget_id=budget_id,
            total_amount=budget.planned_total,
            total_spent=total_spent,
            remaining=remaining,
            utilization_pct=utilization,
            is_overrun=overrun,
            expenses_by_category=by_category,
        )

    async def get_spending_breakdown(
        self,
        budget_id: UUID,
        user_id: UUID,
    ) -> list[CategorySpendResponse]:
        summary = await self.get_budget_summary(budget_id, user_id)
        return [
            CategorySpendResponse(category=cat, amount=amt)
            for cat, amt in summary.expenses_by_category.items()
        ]

    # =========================================================================
    # Expenses
    # =========================================================================

    async def add_expense(
        self,
        budget_id: UUID,
        user_id: UUID,
        data: BudgetExpenseCreate,
    ) -> BudgetExpenseResponse:
        validate_expense_amount(data.amount)

        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)

            # Enforce expense count limit
            expense_count = await uow.budgets.expenses.count(
                uow.budgets.expenses._model.budget_id == budget_id,  # type: ignore[attr-defined]
            )
            if expense_count >= MAX_EXPENSES_PER_BUDGET:
                raise ExpenseLimitError(MAX_EXPENSES_PER_BUDGET)

            if data.category and hasattr(data, "category_id") and data.category_id:
                await validate_category_exists(data.category_id, uow)

            expense = Expense(
                budget_id=budget_id,
                celebration_id=budget.celebration_id,
                title=data.title,
                description=data.description,
                planned_amount=data.amount,
                estimated_amount=data.amount,
                expense_type=data.expense_type,
                expense_source=data.expense_source,
                due_date=data.expense_date,
                is_paid=data.is_paid,
            )
            expense = await uow.budgets.expenses.create(expense)
            await _recompute_budget_totals(budget, uow)
            await uow.commit()

        return BudgetExpenseResponse.model_validate(expense)

    async def update_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        user_id: UUID,
        data: object,  # BudgetExpenseUpdate schema
    ) -> BudgetExpenseResponse:
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            expense = await validate_expense_ownership(expense_id, budget_id, uow)
            update_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            if "amount" in update_dict:
                validate_expense_amount(Decimal(str(update_dict["amount"])))
                update_dict["planned_amount"] = update_dict.pop("amount")
            expense = await uow.budgets.expenses.update(expense, update_dict)
            await _recompute_budget_totals(budget, uow)
            await uow.commit()
        return BudgetExpenseResponse.model_validate(expense)

    async def delete_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            expense = await validate_expense_ownership(expense_id, budget_id, uow)
            await uow.budgets.expenses.soft_delete(expense)
            await _recompute_budget_totals(budget, uow)
            await uow.commit()

    async def list_expenses(
        self,
        budget_id: UUID,
        user_id: UUID,
        filters: object | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            await validate_budget_ownership(budget_id, user_id, uow)
            expenses = await uow.budgets.expenses.find_by_budget(
                budget_id, limit=limit + 1
            )
        responses = [BudgetExpenseResponse.model_validate(e) for e in expenses]
        return _wrap_cursor(responses, limit)

    # =========================================================================
    # Budget categories (admin-managed reference data)
    # =========================================================================

    async def list_categories(self) -> list[BudgetCategoryDefinitionResponse]:
        async with self._uow() as uow:
            categories = await uow.budgets.categories.find_active()
        return [BudgetCategoryDefinitionResponse.model_validate(c) for c in categories]

    async def get_category(self, category_id: UUID) -> BudgetCategoryDefinitionResponse:
        async with self._uow() as uow:
            category = await validate_category_exists(category_id, uow)
        return BudgetCategoryDefinitionResponse.model_validate(category)

    async def create_category(
        self,
        data: object,  # BudgetCategoryCreate schema
        admin_id: UUID,
    ) -> BudgetCategoryDefinitionResponse:
        async with self._uow() as uow:
            create_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            category = ExpenseCategory(**create_dict)
            category = await uow.budgets.categories.create(category)
            await uow.commit()
        return BudgetCategoryDefinitionResponse.model_validate(category)

    async def update_category(
        self,
        category_id: UUID,
        data: object,  # BudgetCategoryUpdate schema
        admin_id: UUID,
    ) -> BudgetCategoryDefinitionResponse:
        async with self._uow() as uow:
            category = await validate_category_exists(category_id, uow)
            update_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            category = await uow.budgets.categories.update(category, update_dict)
            await uow.commit()
        return BudgetCategoryDefinitionResponse.model_validate(category)

    async def delete_category(
        self,
        category_id: UUID,
        admin_id: UUID,
    ) -> None:
        """Delete a category. Raises CategoryInUseError if expenses reference it."""
        async with self._uow() as uow:
            category = await validate_category_exists(category_id, uow)

            # Guard: reject deletion if any expense still references this category
            in_use = await uow.budgets.expenses.exists_where(
                uow.budgets.expenses._model.category_id == category_id,  # type: ignore[attr-defined]
            )
            if in_use:
                raise CategoryInUseError()

            await uow.budgets.categories.soft_delete(category)
            await uow.commit()

    # =========================================================================
    # Budget alerts (simplified — persisted as budget-level threshold)
    # =========================================================================

    async def set_alert(
        self,
        budget_id: UUID,
        user_id: UUID,
        threshold_pct: float,
    ) -> BudgetAlertResponse:
        """Store the alert threshold on the Budget row."""
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            pct_int = max(1, min(100, int(threshold_pct * 100)))
            budget = await uow.budgets.budgets.update(budget, {
                "alert_threshold_pct": pct_int,
                "is_alert_enabled": True,
            })
            await uow.commit()
        return BudgetAlertResponse(
            budget_id=budget_id,
            threshold_pct=threshold_pct,
            message=f"Alert set at {int(threshold_pct * 100)}% utilisation.",
        )

    async def remove_alert(
        self,
        budget_id: UUID,
        alert_id: UUID,
        user_id: UUID,
    ) -> None:
        """Disable the budget alert (no separate alert rows in this model)."""
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)
            await uow.budgets.budgets.update(budget, {"is_alert_enabled": False})
            await uow.commit()

    async def list_alerts(
        self,
        budget_id: UUID,
        user_id: UUID,
    ) -> list[BudgetAlertResponse]:
        async with self._uow() as uow:
            budget = await validate_budget_ownership(budget_id, user_id, uow)

        if not budget.is_alert_enabled:
            return []
        threshold = budget.alert_threshold_pct / 100.0
        return [BudgetAlertResponse(
            budget_id=budget_id,
            threshold_pct=threshold,
            message=f"Alert at {budget.alert_threshold_pct}% utilisation.",
        )]

    async def check_and_trigger_alerts(self, budget_id: UUID) -> list[str]:
        """
        Evaluate current utilisation against the stored threshold.

        Returns a list of human-readable alert messages for any triggered
        threshold. Intended to be called after an expense mutation and the
        result forwarded to the notification service.
        """
        async with self._uow() as uow:
            budget = await validate_budget_exists(budget_id, uow)

        if not budget.is_alert_enabled or not budget.planned_total:
            return []

        utilization = calculate_budget_utilization(budget.actual_total, budget.planned_total)
        threshold = budget.alert_threshold_pct / 100.0
        messages: list[str] = []

        if utilization >= 1.0:
            messages.append(
                f"Budget '{budget_id}' is OVER budget! "
                f"Spent {budget.actual_total} of {budget.planned_total}."
            )
        elif utilization >= threshold:
            pct = int(utilization * 100)
            messages.append(
                f"Budget '{budget_id}' has reached {pct}% utilisation "
                f"({budget.actual_total} of {budget.planned_total})."
            )

        return messages
