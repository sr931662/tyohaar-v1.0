"""Automation Engine CMS controller functions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Query

from app.core.responses import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.schemas.cms.automation import (
    AutomationLogResponse,
    AutomationManualTriggerRequest,
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
    AutomationToggleResponse,
)
from app.services.cms.automation_service import AutomationService


def get_automation_service() -> AutomationService:
    return AutomationService()


AutomationServiceDep = Annotated[AutomationService, Depends(get_automation_service)]


async def create_rule(
    data: AutomationRuleCreate,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationRuleResponse]:
    rule = await svc.create_rule(data, admin_id=uuid.uuid4())
    return SuccessResponse(data=rule, message="Automation rule created")


async def list_rules(
    svc: AutomationServiceDep,
    trigger_event: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    rules, total = await svc.list_rules(
        trigger_event=trigger_event, is_active=is_active, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=[r.model_dump() for r in rules],
        meta=PaginatedMeta(
            page=page, page_size=page_size, total=total,
            total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
        ),
    )


async def get_rule(
    rule_id: uuid.UUID,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationRuleResponse]:
    return SuccessResponse(data=await svc.get_rule(rule_id))


async def update_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationRuleResponse]:
    return SuccessResponse(data=await svc.update_rule(rule_id, data), message="Rule updated")


async def delete_rule(
    rule_id: uuid.UUID,
    svc: AutomationServiceDep,
) -> SuccessResponse[dict]:
    await svc.delete_rule(rule_id)
    return SuccessResponse(data={}, message="Automation rule deleted")


async def toggle_rule(
    rule_id: uuid.UUID,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationToggleResponse]:
    return SuccessResponse(data=await svc.toggle_rule(rule_id))


async def manual_trigger(
    rule_id: uuid.UUID,
    request: AutomationManualTriggerRequest,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationLogResponse]:
    log = await svc.manual_trigger(rule_id, request)
    return SuccessResponse(data=log, message="Rule triggered manually")


async def list_logs(
    svc: AutomationServiceDep,
    rule_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    logs, total = await svc.list_logs(
        rule_id=rule_id, status=status, entity_type=entity_type, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=[l.model_dump() for l in logs],
        meta=PaginatedMeta(
            page=page, page_size=page_size, total=total,
            total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
        ),
    )


async def get_log(
    log_id: uuid.UUID,
    svc: AutomationServiceDep,
) -> SuccessResponse[AutomationLogResponse]:
    return SuccessResponse(data=await svc.get_log(log_id))
