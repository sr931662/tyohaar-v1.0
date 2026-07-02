"""
Global Search Service
=====================
Single search box across all major entity types.
Returns grouped results ranked by relevance.
Uses PostgreSQL ILIKE for case-insensitive matching.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.cms.search import (
    GlobalSearchResponse,
    SearchResultGroup,
    SearchResultItem,
)
from app.services.base import BaseService

_ALL_ENTITY_TYPES = [
    "users", "vendors", "packages", "bookings",
    "payments", "support_tickets", "cities", "categories", "occasions",
]


class SearchService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    async def global_search(
        self,
        *,
        q: str,
        entity_types: list[str] | None = None,
        limit_per_group: int = 5,
    ) -> GlobalSearchResponse:
        start_time = time.monotonic()
        search_types = entity_types or _ALL_ENTITY_TYPES
        groups: list[SearchResultGroup] = []
        total = 0

        async with self._uow() as uow:
            session = uow.session
            assert session is not None

            if "users" in search_types:
                group = await self._search_users(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "vendors" in search_types:
                group = await self._search_vendors(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "packages" in search_types:
                group = await self._search_packages(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "bookings" in search_types:
                group = await self._search_bookings(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "support_tickets" in search_types:
                group = await self._search_tickets(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "categories" in search_types:
                group = await self._search_categories(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

            if "occasions" in search_types:
                group = await self._search_occasions(session, q, limit_per_group)
                if group.total > 0:
                    groups.append(group)
                    total += group.total

        took_ms = round((time.monotonic() - start_time) * 1000, 2)
        return GlobalSearchResponse(
            query=q,
            total_results=total,
            took_ms=took_ms,
            groups=groups,
        )

    async def _search_users(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.users.user import User

        pattern = f"%{q}%"
        stmt = (
            select(User)
            .where(
                User.deleted_at.is_(None),
                or_(
                    User.phone.ilike(pattern),
                    User.email.ilike(pattern) if hasattr(User, "email") else False,
                    User.full_name.ilike(pattern) if hasattr(User, "full_name") else False,
                ),
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="user",
                title=getattr(r, "full_name", None) or r.phone,
                subtitle=r.phone,
                badge=str(r.account_status),
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="users", label="Users", total=len(items), items=items)

    async def _search_vendors(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.vendors.vendor import Vendor

        pattern = f"%{q}%"
        stmt = (
            select(Vendor)
            .where(
                Vendor.deleted_at.is_(None),
                or_(
                    Vendor.business_name.ilike(pattern),
                    Vendor.city.ilike(pattern) if hasattr(Vendor, "city") else False,
                ),
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="vendor",
                title=r.business_name,
                subtitle=getattr(r, "city", None),
                badge=r.verification_status.value,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="vendors", label="Vendors", total=len(items), items=items)

    async def _search_packages(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.packages.package import Package

        pattern = f"%{q}%"
        stmt = (
            select(Package)
            .where(
                Package.deleted_at.is_(None),
                or_(
                    Package.name.ilike(pattern),
                    Package.description.ilike(pattern) if hasattr(Package, "description") else False,
                ),
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="package",
                title=r.name,
                subtitle=f"₹{r.base_price}",
                badge="published" if getattr(r, "is_published", False) else "draft",
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="packages", label="Packages", total=len(items), items=items)

    async def _search_bookings(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.bookings.booking import Booking

        pattern = f"%{q}%"
        # Search by booking reference or UUID prefix
        stmt = (
            select(Booking)
            .where(
                Booking.deleted_at.is_(None),
                or_(
                    Booking.booking_reference.ilike(pattern) if hasattr(Booking, "booking_reference") else False,
                    Booking.status.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="booking",
                title=f"Booking {str(r.id)[:8]}",
                subtitle=f"Status: {r.status}",
                badge=r.status,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="bookings", label="Bookings", total=len(items), items=items)

    async def _search_tickets(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.support.ticket import SupportTicket

        pattern = f"%{q}%"
        stmt = (
            select(SupportTicket)
            .where(
                or_(
                    SupportTicket.subject.ilike(pattern),
                    SupportTicket.description.ilike(pattern) if hasattr(SupportTicket, "description") else False,
                )
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="support_ticket",
                title=r.subject,
                subtitle=f"Status: {r.status}",
                badge=r.status,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="support_tickets", label="Support Tickets", total=len(items), items=items)

    async def _search_categories(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.packages.category import PackageCategory

        pattern = f"%{q}%"
        stmt = select(PackageCategory).where(PackageCategory.name.ilike(pattern)).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="category",
                title=r.name,
                subtitle=getattr(r, "slug", None),
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="categories", label="Categories", total=len(items), items=items)

    async def _search_occasions(self, session: AsyncSession, q: str, limit: int) -> SearchResultGroup:
        from app.models.occasions.occasion import Occasion

        pattern = f"%{q}%"
        stmt = (
            select(Occasion)
            .where(
                or_(
                    Occasion.name.ilike(pattern),
                    Occasion.description.ilike(pattern) if hasattr(Occasion, "description") else False,
                )
            )
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
        items = [
            SearchResultItem(
                id=str(r.id),
                entity_type="occasion",
                title=r.name,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return SearchResultGroup(entity_type="occasions", label="Occasions", total=len(items), items=items)
