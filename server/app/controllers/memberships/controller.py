"""
Memberships Controller — plans, subscriptions, renewals, and feature access.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import MembershipServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.memberships.create import MembershipPlanCreate, SubscribeCreate
from app.schemas.memberships.response import (
    MembershipPlanResponse,
    MembershipResponse,
)
from app.schemas.memberships.update import MembershipPlanUpdate


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Plans ──────────────────────────────────────────────────────────────────────

async def list_plans(
    service: MembershipServiceDep,
) -> SuccessResponse[list[MembershipPlanResponse]]:
    plans = await service.list_plans()
    return SuccessResponse(data=plans, message="Plans retrieved.")


async def get_plan(
    plan_id: uuid.UUID,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipPlanResponse]:
    result = await service.get_plan(plan_id=plan_id)
    return SuccessResponse(data=result, message="Plan retrieved.")


async def create_plan(
    body: MembershipPlanCreate,
    _admin: AdminDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipPlanResponse]:
    result = await service.create_plan(data=body)
    return SuccessResponse(data=result, message="Plan created.")


async def update_plan(
    plan_id: uuid.UUID,
    body: MembershipPlanUpdate,
    _admin: AdminDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipPlanResponse]:
    result = await service.update_plan(plan_id=plan_id, data=body)
    return SuccessResponse(data=result, message="Plan updated.")


async def deactivate_plan(
    plan_id: uuid.UUID,
    _admin: AdminDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipPlanResponse]:
    result = await service.deactivate_plan(plan_id=plan_id)
    return SuccessResponse(data=result, message="Plan deactivated.")


# ── Subscriptions ─────────────────────────────────────────────────────────────

async def subscribe(
    body: SubscribeCreate,
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.subscribe(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Membership subscribed.")


async def get_active_membership(
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.get_active_membership(user_id=current_user.id)
    return SuccessResponse(data=result, message="Active membership retrieved.")


async def get_membership(
    membership_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.get_membership(
        membership_id=membership_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Membership retrieved.")


async def list_user_memberships(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: MembershipServiceDep,
) -> CursorPaginatedResponse[MembershipResponse]:
    page = await service.list_user_memberships(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def cancel_membership(
    membership_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.cancel_membership(
        membership_id=membership_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Membership cancelled.")


async def renew_membership(
    membership_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.renew_membership(
        membership_id=membership_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Membership renewed.")


async def check_membership_feature_access(
    feature: str,
    current_user: CurrentUserDep,
    service: MembershipServiceDep,
) -> SuccessResponse[bool]:
    has_access = await service.check_feature_access(user_id=current_user.id, feature=feature)
    return SuccessResponse(data=has_access, message="Feature access checked.")


# ── Admin membership ops ──────────────────────────────────────────────────────

async def list_all_memberships(
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: MembershipServiceDep,
) -> CursorPaginatedResponse[MembershipResponse]:
    page = await service.list_all_memberships(
        cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def force_expire_membership(
    membership_id: uuid.UUID,
    current_user: AdminDep,
    service: MembershipServiceDep,
) -> SuccessResponse[MembershipResponse]:
    result = await service.force_expire_membership(
        membership_id=membership_id, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Membership expired.")
