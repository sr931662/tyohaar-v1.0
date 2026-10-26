"""
Balloon colour palette routes.

  GET  /balloon-colors              public — the active colours, in display order
  GET  /admin/balloon-colors        admin  — every colour incl. disabled ones
  POST/PATCH/DELETE …               admin  — manage the palette
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_balloon_color_service, get_balloon_finish_service
from app.core.permissions import AdminDep
from app.core.responses import SuccessResponse
from app.schemas.colors import (
    BalloonColorCreate,
    BalloonColorReorder,
    BalloonColorResponse,
    BalloonColorUpdate,
    BalloonFinishCreate,
    BalloonFinishResponse,
    BalloonFinishUpdate,
)
from app.services.colors.service import BalloonColorService, BalloonFinishService

router = APIRouter(tags=["Balloon colours"])
Service = Annotated[BalloonColorService, Depends(get_balloon_color_service)]
FinishService = Annotated[BalloonFinishService, Depends(get_balloon_finish_service)]


@router.get("/balloon-colors", response_model=SuccessResponse[list[BalloonColorResponse]],
            summary="Active balloon colours", operation_id="colors_list_public")
async def list_public(service: Service):
    return SuccessResponse(data=await service.list(active_only=True), message="Colours retrieved.")


@router.get("/admin/balloon-colors", response_model=SuccessResponse[list[BalloonColorResponse]],
            summary="All balloon colours (admin)", operation_id="colors_list_admin")
async def list_admin(_admin: AdminDep, service: Service):
    return SuccessResponse(data=await service.list(active_only=False), message="Colours retrieved.")


@router.post("/admin/balloon-colors", response_model=SuccessResponse[BalloonColorResponse],
             status_code=status.HTTP_201_CREATED, summary="Add a colour", operation_id="colors_create")
async def create(body: BalloonColorCreate, _admin: AdminDep, service: Service):
    return SuccessResponse(data=await service.create(body), message="Colour added.")


# Static segment before {color_id} so "reorder" is never read as an id.
@router.post("/admin/balloon-colors/reorder", response_model=SuccessResponse[list[BalloonColorResponse]],
             summary="Set the display order", operation_id="colors_reorder")
async def reorder(body: BalloonColorReorder, _admin: AdminDep, service: Service):
    return SuccessResponse(data=await service.reorder(body.ids), message="Order saved.")


@router.patch("/admin/balloon-colors/{color_id}", response_model=SuccessResponse[BalloonColorResponse],
              summary="Edit a colour", operation_id="colors_update")
async def update(color_id: uuid.UUID, body: BalloonColorUpdate, _admin: AdminDep, service: Service):
    return SuccessResponse(data=await service.update(color_id, body), message="Colour updated.")


@router.delete("/admin/balloon-colors/{color_id}", response_model=SuccessResponse[None],
               summary="Remove a colour", operation_id="colors_delete")
async def delete(color_id: uuid.UUID, _admin: AdminDep, service: Service):
    await service.delete(color_id)
    return SuccessResponse(data=None, message="Colour removed.")


# ── Finishes (matte / pastel / chrome …) ─────────────────────────────────────

@router.get("/balloon-finishes", response_model=SuccessResponse[list[BalloonFinishResponse]],
            summary="Active balloon finishes", operation_id="finishes_list_public")
async def list_finishes_public(service: FinishService):
    return SuccessResponse(data=await service.list(active_only=True), message="Finishes retrieved.")


@router.get("/admin/balloon-finishes", response_model=SuccessResponse[list[BalloonFinishResponse]],
            summary="All balloon finishes (admin)", operation_id="finishes_list_admin")
async def list_finishes_admin(_admin: AdminDep, service: FinishService):
    return SuccessResponse(data=await service.list(active_only=False), message="Finishes retrieved.")


@router.post("/admin/balloon-finishes", response_model=SuccessResponse[BalloonFinishResponse],
             status_code=status.HTTP_201_CREATED, summary="Add a finish", operation_id="finishes_create")
async def create_finish(body: BalloonFinishCreate, _admin: AdminDep, service: FinishService):
    return SuccessResponse(data=await service.create(body), message="Finish added.")


@router.post("/admin/balloon-finishes/reorder", response_model=SuccessResponse[list[BalloonFinishResponse]],
             summary="Set the finish display order", operation_id="finishes_reorder")
async def reorder_finishes(body: BalloonColorReorder, _admin: AdminDep, service: FinishService):
    return SuccessResponse(data=await service.reorder(body.ids), message="Order saved.")


@router.patch("/admin/balloon-finishes/{finish_id}", response_model=SuccessResponse[BalloonFinishResponse],
              summary="Edit a finish", operation_id="finishes_update")
async def update_finish(finish_id: uuid.UUID, body: BalloonFinishUpdate, _admin: AdminDep, service: FinishService):
    return SuccessResponse(data=await service.update(finish_id, body), message="Finish updated.")


@router.delete("/admin/balloon-finishes/{finish_id}", response_model=SuccessResponse[None],
               summary="Remove a finish", operation_id="finishes_delete")
async def delete_finish(finish_id: uuid.UUID, _admin: AdminDep, service: FinishService):
    await service.delete(finish_id)
    return SuccessResponse(data=None, message="Finish removed.")
