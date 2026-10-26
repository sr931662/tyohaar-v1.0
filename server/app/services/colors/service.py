"""
BalloonColorService — the managed balloon colour palette.

Admins own the list; customers (and vendors, read-only) see the active
colours. Booking validation calls `active_hex_codes` so only a colour that is
currently offered can be ordered.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal
from app.models.common.balloon_color import BalloonColor
from app.models.common.balloon_finish import BalloonFinish
from app.schemas.colors import (
    BalloonColorCreate,
    BalloonColorResponse,
    BalloonColorUpdate,
    BalloonFinishCreate,
    BalloonFinishResponse,
    BalloonFinishUpdate,
)
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError

MAX_COLORS = 60


class BalloonColorService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    async def list(self, *, active_only: bool) -> list[BalloonColorResponse]:
        async with self._uow() as uow:
            stmt = select(BalloonColor).order_by(BalloonColor.sort_order, func.lower(BalloonColor.name))
            if active_only:
                stmt = stmt.where(BalloonColor.is_active.is_(True))
            rows = (await uow.session.execute(stmt)).scalars().all()
            return [BalloonColorResponse.model_validate(r) for r in rows]

    @staticmethod
    async def active_hex_codes(uow) -> set[str]:
        """Lower-cased hex codes a customer may currently order."""
        rows = (await uow.session.execute(
            select(BalloonColor.hex_code).where(BalloonColor.is_active.is_(True))
        )).scalars().all()
        return {h.lower() for h in rows}

    @staticmethod
    async def resolve_finish(uow, name: str) -> str | None:
        """The canonical name of an *active* finish matching `name`, or None."""
        row = (await uow.session.execute(
            select(BalloonFinish.name).where(
                func.lower(BalloonFinish.name) == name.strip().lower(), BalloonFinish.is_active.is_(True)
            )
        )).scalar_one_or_none()
        return row

    async def create(self, data: BalloonColorCreate) -> BalloonColorResponse:
        try:
            async with self._uow() as uow:
                total = (await uow.session.execute(select(func.count()).select_from(BalloonColor))).scalar_one()
                if total >= MAX_COLORS:
                    raise BusinessRuleError(f"The palette is limited to {MAX_COLORS} colours.")
                next_order = (await uow.session.execute(
                    select(func.coalesce(func.max(BalloonColor.sort_order), -1) + 1)
                )).scalar_one()
                color = BalloonColor(
                    name=data.name.strip(), hex_code=data.hex_code, is_active=data.is_active, sort_order=next_order
                )
                uow.session.add(color)
                await uow.session.flush()
                return BalloonColorResponse.model_validate(color)
        except IntegrityError as exc:
            raise ConflictError("A colour with this name or hex code already exists.") from exc

    async def update(self, color_id: uuid.UUID, data: BalloonColorUpdate) -> BalloonColorResponse:
        try:
            async with self._uow() as uow:
                color = await uow.session.get(BalloonColor, color_id)
                if color is None:
                    raise NotFoundError("Colour", str(color_id))
                changes = data.model_dump(exclude_unset=True)
                if "name" in changes and changes["name"]:
                    color.name = changes["name"].strip()
                if changes.get("hex_code"):
                    color.hex_code = changes["hex_code"]
                if changes.get("is_active") is not None:
                    color.is_active = changes["is_active"]
                await uow.session.flush()
                return BalloonColorResponse.model_validate(color)
        except IntegrityError as exc:
            raise ConflictError("A colour with this name or hex code already exists.") from exc

    async def delete(self, color_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            color = await uow.session.get(BalloonColor, color_id)
            if color is None:
                raise NotFoundError("Colour", str(color_id))
            # Bookings keep the hex they chose, so deleting is safe for
            # history; but the palette must keep at least two colours to be
            # a usable dual-colour choice.
            remaining = (await uow.session.execute(
                select(func.count()).select_from(BalloonColor).where(
                    BalloonColor.id != color_id, BalloonColor.is_active.is_(True)
                )
            )).scalar_one()
            if color.is_active and remaining < 2:
                raise BusinessRuleError("Keep at least two active colours so customers can pick a combination.")
            await uow.session.delete(color)

    async def reorder(self, ids: list[uuid.UUID]) -> list[BalloonColorResponse]:
        async with self._uow() as uow:
            rows = {c.id: c for c in (await uow.session.execute(select(BalloonColor))).scalars().all()}
            if set(ids) - set(rows):
                raise NotFoundError("Colour")
            position = 0
            for cid in ids:
                rows[cid].sort_order = position
                position += 1
            # Anything not mentioned keeps its relative order after the listed ones.
            for cid, color in sorted(rows.items(), key=lambda kv: kv[1].sort_order):
                if cid not in ids:
                    color.sort_order = position
                    position += 1
            await uow.session.flush()
        return await self.list(active_only=False)


class BalloonFinishService(BaseService):
    """Admin-managed balloon finishes (matte, pastel, chrome …)."""

    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    async def list(self, *, active_only: bool) -> list[BalloonFinishResponse]:
        async with self._uow() as uow:
            stmt = select(BalloonFinish).order_by(BalloonFinish.sort_order, func.lower(BalloonFinish.name))
            if active_only:
                stmt = stmt.where(BalloonFinish.is_active.is_(True))
            rows = (await uow.session.execute(stmt)).scalars().all()
            return [BalloonFinishResponse.model_validate(r) for r in rows]

    async def create(self, data: BalloonFinishCreate) -> BalloonFinishResponse:
        try:
            async with self._uow() as uow:
                next_order = (await uow.session.execute(
                    select(func.coalesce(func.max(BalloonFinish.sort_order), -1) + 1)
                )).scalar_one()
                finish = BalloonFinish(name=data.name.strip(), is_active=data.is_active, sort_order=next_order)
                uow.session.add(finish)
                await uow.session.flush()
                return BalloonFinishResponse.model_validate(finish)
        except IntegrityError as exc:
            raise ConflictError("A finish with this name already exists.") from exc

    async def update(self, finish_id: uuid.UUID, data: BalloonFinishUpdate) -> BalloonFinishResponse:
        try:
            async with self._uow() as uow:
                finish = await uow.session.get(BalloonFinish, finish_id)
                if finish is None:
                    raise NotFoundError("Finish", str(finish_id))
                changes = data.model_dump(exclude_unset=True)
                if changes.get("name"):
                    finish.name = changes["name"].strip()
                if changes.get("is_active") is not None:
                    finish.is_active = changes["is_active"]
                await uow.session.flush()
                return BalloonFinishResponse.model_validate(finish)
        except IntegrityError as exc:
            raise ConflictError("A finish with this name already exists.") from exc

    async def delete(self, finish_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            finish = await uow.session.get(BalloonFinish, finish_id)
            if finish is None:
                raise NotFoundError("Finish", str(finish_id))
            await uow.session.delete(finish)

    async def reorder(self, ids: list[uuid.UUID]) -> list[BalloonFinishResponse]:
        async with self._uow() as uow:
            rows = {f.id: f for f in (await uow.session.execute(select(BalloonFinish))).scalars().all()}
            if set(ids) - set(rows):
                raise NotFoundError("Finish")
            position = 0
            for fid in ids:
                rows[fid].sort_order = position
                position += 1
            for fid, finish in sorted(rows.items(), key=lambda kv: kv[1].sort_order):
                if fid not in ids:
                    finish.sort_order = position
                    position += 1
            await uow.session.flush()
        return await self.list(active_only=False)
