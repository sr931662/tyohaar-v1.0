"""
Referrals Controller — referral codes, applications, rewards, and stats.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import ReferralServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.referrals.create import ReferralApplyCreate
from app.schemas.referrals.response import (
    ReferralResponse,
    ReferralRewardResponse,
    ReferralStatsResponse,
)
from app.services.referrals.service import ReferralCodeResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def get_referral_code(
    current_user: CurrentUserDep,
    service: ReferralServiceDep,
) -> SuccessResponse[ReferralCodeResponse]:
    result = await service.get_referral_code(user_id=current_user.id)
    return SuccessResponse(data=result, message="Referral code retrieved.")


async def apply_referral_code(
    body: ReferralApplyCreate,
    current_user: CurrentUserDep,
    service: ReferralServiceDep,
) -> SuccessResponse[ReferralResponse]:
    result = await service.apply_referral_code(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Referral code applied.")


async def trigger_referral_rewards(
    referral_id: uuid.UUID,
    current_user: AdminDep,
    service: ReferralServiceDep,
) -> SuccessResponse[None]:
    await service.trigger_referral_rewards(
        referral_id=referral_id, admin_id=current_user.id
    )
    return SuccessResponse(data=None, message="Referral rewards triggered.")


async def activate_referral_reward(
    reward_id: uuid.UUID,
    current_user: AdminDep,
    service: ReferralServiceDep,
) -> SuccessResponse[ReferralRewardResponse]:
    result = await service.activate_referral_reward(
        reward_id=reward_id, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Referral reward activated.")


async def get_referral_stats(
    current_user: CurrentUserDep,
    service: ReferralServiceDep,
) -> SuccessResponse[ReferralStatsResponse]:
    result = await service.get_referral_stats(user_id=current_user.id)
    return SuccessResponse(data=result, message="Referral stats retrieved.")


async def list_referrals(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: ReferralServiceDep,
) -> CursorPaginatedResponse[ReferralResponse]:
    page = await service.list_referrals(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def list_rewards(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: ReferralServiceDep,
) -> CursorPaginatedResponse[ReferralRewardResponse]:
    page = await service.list_rewards(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def get_reward(
    reward_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ReferralServiceDep,
) -> SuccessResponse[ReferralRewardResponse]:
    result = await service.get_reward(reward_id=reward_id, user_id=current_user.id)
    return SuccessResponse(data=result, message="Reward retrieved.")
