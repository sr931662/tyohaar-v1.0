"""
Budget repository — Budget, Expense, ExpenseCategory.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budgets.budget import Budget
from app.models.budgets.category import ExpenseCategory
from app.models.budgets.expense import Expense
from app.models.enums import BudgetLifecycleStatus, ExpenseSource, ExpenseType
from app.repositories.base import BaseRepository


class ExpenseCategoryRepository(BaseRepository[ExpenseCategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ExpenseCategory)

    async def find_root_categories(self) -> list[ExpenseCategory]:
        return await self.find_many(
            ExpenseCategory.parent_id.is_(None),
            order_by=ExpenseCategory.display_order.asc(),
        )

    async def find_children(self, parent_id: uuid.UUID) -> list[ExpenseCategory]:
        return await self.find_many(
            ExpenseCategory.parent_id == parent_id,
            order_by=ExpenseCategory.display_order.asc(),
        )

    async def find_system_categories(self) -> list[ExpenseCategory]:
        return await self.find_many(ExpenseCategory.is_system == True)  # noqa: E712

    async def find_by_slug(self, slug: str) -> ExpenseCategory | None:
        return await self.find_one(ExpenseCategory.slug == slug)

    async def find_active(self) -> list[ExpenseCategory]:
        return await self.find_many(
            ExpenseCategory.is_active == True,  # noqa: E712
            order_by=ExpenseCategory.display_order.asc(),
        )

    async def get_with_children(self, category_id: uuid.UUID) -> ExpenseCategory | None:
        return await self.get_by_id(
            category_id,
            options=[selectinload(ExpenseCategory.children)],
        )


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Budget)

    async def find_by_celebration(
        self,
        celebration_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> list[Budget]:
        return await self.find_many(
            Budget.celebration_id == celebration_id,
            order_by=Budget.created_at.desc(),
            include_deleted=include_deleted,
        )

    async def get_active_for_celebration(self, celebration_id: uuid.UUID) -> Budget | None:
        """
        Returns the single ACTIVE budget for a celebration.
        The partial unique index (WHERE budget_status = 'active' AND deleted_at IS NULL)
        guarantees at most one row matches.
        """
        return await self.find_one(
            Budget.celebration_id == celebration_id,
            Budget.budget_status == BudgetLifecycleStatus.ACTIVE,
        )

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Budget]:
        return await self.find_many(
            Budget.customer_id == customer_id,
            order_by=Budget.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_status(
        self,
        status: BudgetLifecycleStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Budget]:
        return await self.find_many(
            Budget.budget_status == status,
            skip=skip,
            limit=limit,
        )

    async def find_over_budget(self) -> list[Budget]:
        """Return ACTIVE budgets where actual_total exceeds estimated_total."""
        return await self.find_many(
            Budget.budget_status == BudgetLifecycleStatus.ACTIVE,
            Budget.actual_total > Budget.estimated_total,
        )

    async def find_with_alerts_due(self) -> list[Budget]:
        """Return budgets where alert_threshold is breached and alert is enabled."""
        return await self.find_many(
            Budget.budget_status == BudgetLifecycleStatus.ACTIVE,
            Budget.is_alert_enabled == True,  # noqa: E712
        )

    async def get_with_expenses(self, budget_id: uuid.UUID) -> Budget | None:
        return await self.get_by_id(
            budget_id,
            options=[selectinload(Budget.expenses)],
        )


class ExpenseRepository(BaseRepository[Expense]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Expense)

    async def find_by_budget(
        self,
        budget_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            order_by=Expense.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_celebration(
        self,
        celebration_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Expense]:
        return await self.find_many(
            Expense.celebration_id == celebration_id,
            order_by=Expense.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_category(
        self,
        budget_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.category_id == category_id,
        )

    async def find_by_type(
        self,
        budget_id: uuid.UUID,
        expense_type: ExpenseType,
    ) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.expense_type == expense_type,
        )

    async def find_by_source(
        self,
        budget_id: uuid.UUID,
        source: ExpenseSource,
    ) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.expense_source == source,
        )

    async def find_unpaid(self, budget_id: uuid.UUID) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.is_paid == False,  # noqa: E712
        )

    async def find_due_before(
        self,
        budget_id: uuid.UUID,
        cutoff_date: str,
    ) -> list[Expense]:
        from datetime import date as date_type
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.due_date <= cutoff_date,
            Expense.is_paid == False,  # noqa: E712
        )

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[Expense]:
        return await self.find_many(Expense.booking_id == booking_id)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[Expense]:
        return await self.find_many(Expense.payment_id == payment_id)

    async def find_recurring(self, budget_id: uuid.UUID) -> list[Expense]:
        return await self.find_many(
            Expense.budget_id == budget_id,
            Expense.is_recurring == True,  # noqa: E712
        )

    async def get_totals_by_category(self, budget_id: uuid.UUID) -> dict[str, dict]:
        """
        Return per-category totals for a budget.
        Returns: {category_id_str: {estimated, planned, actual}}
        """
        stmt = (
            select(
                Expense.category_id,
                func.sum(Expense.estimated_amount).label("estimated"),
                func.sum(Expense.planned_amount).label("planned"),
                func.sum(Expense.actual_amount).label("actual"),
            )
            .where(Expense.budget_id == budget_id)
            .where(Expense.deleted_at.is_(None))
            .group_by(Expense.category_id)
        )
        result = await self._session.execute(stmt)
        return {
            str(row.category_id): {
                "estimated": row.estimated,
                "planned": row.planned,
                "actual": row.actual,
            }
            for row in result.all()
        }


class BudgetRepositoryAggregate:
    """Groups budget-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.budgets = BudgetRepository(session)
        self.expenses = ExpenseRepository(session)
        self.categories = ExpenseCategoryRepository(session)
