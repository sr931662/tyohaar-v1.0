"""Import / Export CMS controller functions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Query, UploadFile, File, Form
from fastapi.responses import Response

from app.core.responses import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.schemas.cms.io import (
    ExportLogResponse,
    ExportRequest,
    ExportTriggerResponse,
    ImportLogResponse,
    ImportPreviewResponse,
    ImportUndoResponse,
)
from app.services.cms.io_service import IOService


def get_io_service() -> IOService:
    return IOService()


IOServiceDep = Annotated[IOService, Depends(get_io_service)]


async def get_import_template(
    entity_type: str,
    svc: IOServiceDep,
) -> Response:
    content = await svc.get_import_template(entity_type)
    filename = f"tyohaar_{entity_type}_template.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def validate_import(
    svc: IOServiceDep,
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    is_dry_run: bool = Form(default=False),
) -> SuccessResponse[dict]:
    content = await file.read()
    preview, log_id = await svc.validate_and_preview(
        content=content,
        filename=file.filename or "upload.xlsx",
        entity_type=entity_type,
        admin_id=uuid.uuid4(),  # In production: inject from CurrentUserDep
        is_dry_run=is_dry_run,
    )
    return SuccessResponse(
        data={"log_id": str(log_id), "preview": preview.model_dump()},
        message="Validation complete",
    )


async def execute_import(
    svc: IOServiceDep,
    file: UploadFile = File(...),
    log_id: uuid.UUID = Form(...),
    overwrite_duplicates: bool = Form(default=False),
) -> SuccessResponse[ImportLogResponse]:
    content = await file.read()
    result = await svc.execute_import(
        log_id=log_id,
        content=content,
        overwrite_duplicates=overwrite_duplicates,
    )
    return SuccessResponse(data=result, message="Import executed")


async def undo_import(
    log_id: uuid.UUID,
    svc: IOServiceDep,
) -> SuccessResponse[ImportUndoResponse]:
    return SuccessResponse(data=await svc.undo_import(log_id))


async def list_import_logs(
    svc: IOServiceDep,
    entity_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    logs, total = await svc.get_import_logs(
        entity_type=entity_type, status=status, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=[l.model_dump() for l in logs],
        meta=PaginatedMeta(
            page=page, page_size=page_size, total=total,
            total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
        ),
    )


async def get_import_log(log_id: uuid.UUID, svc: IOServiceDep) -> SuccessResponse[ImportLogResponse]:
    return SuccessResponse(data=await svc.get_import_log(log_id))


async def trigger_export(
    request: ExportRequest,
    svc: IOServiceDep,
) -> SuccessResponse[ExportTriggerResponse]:
    result = await svc.trigger_export(request=request, admin_id=uuid.uuid4())
    return SuccessResponse(data=result, message="Export triggered")


async def list_export_logs(
    svc: IOServiceDep,
    entity_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    logs, total = await svc.get_export_logs(
        entity_type=entity_type, status=status, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=[l.model_dump() for l in logs],
        meta=PaginatedMeta(
            page=page, page_size=page_size, total=total,
            total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
        ),
    )


async def get_export_log(log_id: uuid.UUID, svc: IOServiceDep) -> SuccessResponse[ExportLogResponse]:
    return SuccessResponse(data=await svc.get_export_log(log_id))
