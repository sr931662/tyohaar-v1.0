"""
Budgets Routes — budgets, expenses, categories, and alerts.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.budgets import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.budgets.response import (
    BudgetCategoryResponse,
    BudgetExpenseResponse,
    BudgetResponse,
)
from app.services.budgets.service import (
    BudgetAlertResponse,
    BudgetSummaryResponse,
    CategorySpendResponse,
)

router = APIRouter(prefix="/budgets", tags=["Budgets"])

# ── Categories (static, must precede /{budget_id}) ───────────────────────────

router.add_api_route(
    "/categories",
    ctrl.list_categories,
    methods=["GET"],
    response_model=SuccessResponse[list[BudgetCategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Budget Categories",
    description="Return all budget expense categories. Public endpoint.",
    operation_id="budgets_list_categories",
)

router.add_api_route(
    "/categories",
    ctrl.create_category,
    methods=["POST"],
    response_model=SuccessResponse[BudgetCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Budget Category (Admin)",
    description="Create a new budget expense category. Admin access required.",
    operation_id="budgets_create_category",
)

router.add_api_route(
    "/categories/{category_id}",
    ctrl.get_category,
    methods=["GET"],
    response_model=SuccessResponse[BudgetCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Budget Category",
    description="Return a single budget category by ID.",
    operation_id="budgets_get_category",
)

router.add_api_route(
    "/categories/{category_id}",
    ctrl.update_category,
    methods=["PUT"],
    response_model=SuccessResponse[BudgetCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Budget Category (Admin)",
    description="Update a budget expense category. Admin access required.",
    operation_id="budgets_update_category",
)

router.add_api_route(
    "/categories/{category_id}",
    ctrl.delete_category,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Budget Category (Admin)",
    description="Delete a budget expense category. Admin access required.",
    operation_id="budgets_delete_category",
)

# ── Budget CRUD ───────────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.list_budgets,
    methods=["GET"],
    response_model=CursorPaginatedResponse[BudgetResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Budgets",
    description="Return a cursor-paginated list of budgets for the authenticated user.",
    operation_id="budgets_list_budgets",
)

router.add_api_route(
    "",
    ctrl.create_budget,
    methods=["POST"],
    response_model=SuccessResponse[BudgetResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Budget",
    description="Create a new budget for the authenticated user.",
    operation_id="budgets_create_budget",
)

router.add_api_route(
    "/{budget_id}",
    ctrl.get_budget,
    methods=["GET"],
    response_model=SuccessResponse[BudgetResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Budget",
    description="Return a single budget by ID. User ownership required.",
    operation_id="budgets_get_budget",
)

router.add_api_route(
    "/{budget_id}",
    ctrl.update_budget,
    methods=["PUT"],
    response_model=SuccessResponse[BudgetResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Budget",
    description="Update top-level fields on a budget. User ownership required.",
    operation_id="budgets_update_budget",
)

router.add_api_route(
    "/{budget_id}",
    ctrl.delete_budget,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Budget",
    description="Delete a budget and all its associated expenses and alerts.",
    operation_id="budgets_delete_budget",
)

# ── Budget analytics ──────────────────────────────────────────────────────────

router.add_api_route(
    "/{budget_id}/summary",
    ctrl.get_budget_summary,
    methods=["GET"],
    response_model=SuccessResponse[BudgetSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Budget Summary",
    description="Return aggregated spending vs. allocation summary for a budget.",
    operation_id="budgets_get_budget_summary",
)

router.add_api_route(
    "/{budget_id}/breakdown",
    ctrl.get_spending_breakdown,
    methods=["GET"],
    response_model=SuccessResponse[list[CategorySpendResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Spending Breakdown",
    description="Return per-category spending breakdown for a budget.",
    operation_id="budgets_get_spending_breakdown",
)

# ── Expenses ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{budget_id}/expenses",
    ctrl.list_expenses,
    methods=["GET"],
    response_model=CursorPaginatedResponse[BudgetExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="List Expenses",
    description="Return a cursor-paginated list of expenses for a budget.",
    operation_id="budgets_list_expenses",
)

router.add_api_route(
    "/{budget_id}/expenses",
    ctrl.add_expense,
    methods=["POST"],
    response_model=SuccessResponse[BudgetExpenseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Expense",
    description="Record a new expense under a budget.",
    operation_id="budgets_add_expense",
)

router.add_api_route(
    "/{budget_id}/expenses/{expense_id}",
    ctrl.update_expense,
    methods=["PUT"],
    response_model=SuccessResponse[BudgetExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Expense",
    description="Update an existing budget expense record.",
    operation_id="budgets_update_expense",
)

router.add_api_route(
    "/{budget_id}/expenses/{expense_id}",
    ctrl.delete_expense,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Expense",
    description="Remove an expense record from a budget.",
    operation_id="budgets_delete_expense",
)

# ── Alerts ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{budget_id}/alerts",
    ctrl.list_alerts,
    methods=["GET"],
    response_model=SuccessResponse[list[BudgetAlertResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Budget Alerts",
    description="Return all spending alerts configured for a budget.",
    operation_id="budgets_list_alerts",
)

router.add_api_route(
    "/{budget_id}/alerts",
    ctrl.set_alert,
    methods=["POST"],
    response_model=SuccessResponse[BudgetAlertResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set Budget Alert",
    description="Configure a spending threshold alert for a budget.",
    operation_id="budgets_set_alert",
)

router.add_api_route(
    "/{budget_id}/alerts/{alert_id}",
    ctrl.remove_alert,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Remove Budget Alert",
    description="Remove a spending alert from a budget.",
    operation_id="budgets_remove_alert",
)
