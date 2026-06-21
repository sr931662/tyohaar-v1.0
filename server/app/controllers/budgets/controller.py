"""
Budgets Controller — budgets, expenses, categories, and alerts.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import BudgetServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.budgets.create import (
    BudgetAlertCreate,
    BudgetCategoryCreate,
    BudgetCreate,
    BudgetExpenseCreate,
)
from app.schemas.budgets.response import (
    BudgetCategoryResponse,
    BudgetExpenseResponse,
    BudgetResponse,
)
from app.schemas.budgets.update import (
    BudgetCategoryUpdate,
    BudgetExpenseUpdate,
    BudgetUpdate,
)
from app.services.budgets.service import (
    BudgetAlertResponse,
    BudgetSummaryResponse,
    CategorySpendResponse,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Budgets ───────────────────────────────────────────────────────────────────

async def create_budget(
    body: BudgetCreate,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetResponse]:
    result = await service.create_budget(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Budget created.")


async def get_budget(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetResponse]:
    result = await service.get_budget(budget_id=budget_id, user_id=current_user.id)
    return SuccessResponse(data=result, message="Budget retrieved.")


async def list_budgets(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: BudgetServiceDep,
) -> CursorPaginatedResponse[BudgetResponse]:
    page = await service.list_budgets(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def update_budget(
    budget_id: uuid.UUID,
    body: BudgetUpdate,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetResponse]:
    result = await service.update_budget(
        budget_id=budget_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Budget updated.")


async def delete_budget(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[None]:
    await service.delete_budget(budget_id=budget_id, user_id=current_user.id)
    return SuccessResponse(data=None, message="Budget deleted.")


async def get_budget_summary(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetSummaryResponse]:
    result = await service.get_budget_summary(
        budget_id=budget_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Budget summary retrieved.")


async def get_spending_breakdown(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[list[CategorySpendResponse]]:
    result = await service.get_spending_breakdown(
        budget_id=budget_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Spending breakdown retrieved.")


# ── Expenses ──────────────────────────────────────────────────────────────────

async def add_expense(
    budget_id: uuid.UUID,
    body: BudgetExpenseCreate,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetExpenseResponse]:
    result = await service.add_expense(
        budget_id=budget_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Expense added.")


async def update_expense(
    budget_id: uuid.UUID,
    expense_id: uuid.UUID,
    body: BudgetExpenseUpdate,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetExpenseResponse]:
    result = await service.update_expense(
        budget_id=budget_id, expense_id=expense_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Expense updated.")


async def delete_expense(
    budget_id: uuid.UUID,
    expense_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[None]:
    await service.delete_expense(
        budget_id=budget_id, expense_id=expense_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Expense deleted.")


async def list_expenses(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: BudgetServiceDep,
) -> CursorPaginatedResponse[BudgetExpenseResponse]:
    page = await service.list_expenses(
        budget_id=budget_id,
        user_id=current_user.id,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


# ── Categories ────────────────────────────────────────────────────────────────

async def list_categories(
    service: BudgetServiceDep,
) -> SuccessResponse[list[BudgetCategoryResponse]]:
    categories = await service.list_categories()
    return SuccessResponse(data=categories, message="Categories retrieved.")


async def get_category(
    category_id: uuid.UUID,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetCategoryResponse]:
    result = await service.get_category(category_id=category_id)
    return SuccessResponse(data=result, message="Category retrieved.")


async def create_category(
    body: BudgetCategoryCreate,
    _admin: AdminDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetCategoryResponse]:
    result = await service.create_category(data=body)
    return SuccessResponse(data=result, message="Category created.")


async def update_category(
    category_id: uuid.UUID,
    body: BudgetCategoryUpdate,
    _admin: AdminDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetCategoryResponse]:
    result = await service.update_category(category_id=category_id, data=body)
    return SuccessResponse(data=result, message="Category updated.")


async def delete_category(
    category_id: uuid.UUID,
    _admin: AdminDep,
    service: BudgetServiceDep,
) -> SuccessResponse[None]:
    await service.delete_category(category_id=category_id)
    return SuccessResponse(data=None, message="Category deleted.")


# ── Alerts ────────────────────────────────────────────────────────────────────

async def set_alert(
    budget_id: uuid.UUID,
    body: BudgetAlertCreate,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[BudgetAlertResponse]:
    result = await service.set_alert(
        budget_id=budget_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Alert set.")


async def remove_alert(
    budget_id: uuid.UUID,
    alert_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[None]:
    await service.remove_alert(
        budget_id=budget_id, alert_id=alert_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Alert removed.")


async def list_alerts(
    budget_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BudgetServiceDep,
) -> SuccessResponse[list[BudgetAlertResponse]]:
    alerts = await service.list_alerts(budget_id=budget_id, user_id=current_user.id)
    return SuccessResponse(data=alerts, message="Alerts retrieved.")
