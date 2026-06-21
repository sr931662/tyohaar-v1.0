"""
Wallets Controller — wallet lifecycle, balance operations, transactions, and rewards.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, Query

from app.core.current_user import CurrentUserDep
from app.core.dependencies import WalletServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.wallets.create import UserRewardCreate
from app.schemas.wallets.filters import WalletTransactionFilters
from app.schemas.wallets.response import (
    UserRewardResponse,
    WalletResponse,
    WalletTransactionResponse,
)
from app.services.wallets.service import RewardBalanceResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def create_wallet(
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletResponse]:
    result = await service.create_wallet(user_id=current_user.id)
    return SuccessResponse(data=result, message="Wallet created.")


async def get_wallet(
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletResponse]:
    result = await service.get_wallet(user_id=current_user.id)
    return SuccessResponse(data=result, message="Wallet retrieved.")


async def get_wallet_by_id(
    wallet_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletResponse]:
    result = await service.get_wallet_by_id(wallet_id=wallet_id, user_id=current_user.id)
    return SuccessResponse(data=result, message="Wallet retrieved.")


async def credit_wallet(
    user_id: uuid.UUID,
    _admin: AdminDep,
    service: WalletServiceDep,
    amount: Decimal = Query(...),
    description: str = Query(...),
    reference_id: uuid.UUID | None = Query(default=None),
    reference_type: str | None = Query(default=None),
) -> SuccessResponse[WalletTransactionResponse]:
    result = await service.credit_wallet(
        user_id=user_id,
        amount=amount,
        description=description,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    return SuccessResponse(data=result, message="Wallet credited.")


async def debit_wallet(
    user_id: uuid.UUID,
    _admin: AdminDep,
    service: WalletServiceDep,
    amount: Decimal = Query(...),
    description: str = Query(...),
    reference_id: uuid.UUID | None = Query(default=None),
    reference_type: str | None = Query(default=None),
) -> SuccessResponse[WalletTransactionResponse]:
    result = await service.debit_wallet(
        user_id=user_id,
        amount=amount,
        description=description,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    return SuccessResponse(data=result, message="Wallet debited.")


async def freeze_wallet(
    wallet_id: uuid.UUID,
    current_user: AdminDep,
    service: WalletServiceDep,
    reason: str = Query(...),
) -> SuccessResponse[WalletResponse]:
    result = await service.freeze_wallet(
        wallet_id=wallet_id, admin_id=current_user.id, reason=reason
    )
    return SuccessResponse(data=result, message="Wallet frozen.")


async def unfreeze_wallet(
    wallet_id: uuid.UUID,
    current_user: AdminDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletResponse]:
    result = await service.unfreeze_wallet(wallet_id=wallet_id, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Wallet unfrozen.")


async def close_wallet(
    wallet_id: uuid.UUID,
    current_user: AdminDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletResponse]:
    result = await service.close_wallet(wallet_id=wallet_id, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Wallet closed.")


async def list_transactions(
    current_user: CurrentUserDep,
    filters: Annotated[WalletTransactionFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: WalletServiceDep,
) -> CursorPaginatedResponse[WalletTransactionResponse]:
    page = await service.list_transactions(
        user_id=current_user.id,
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def get_transaction(
    tx_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[WalletTransactionResponse]:
    result = await service.get_transaction(user_id=current_user.id, tx_id=tx_id)
    return SuccessResponse(data=result, message="Transaction retrieved.")


async def award_reward(
    user_id: uuid.UUID,
    body: UserRewardCreate,
    _admin: AdminDep,
    service: WalletServiceDep,
) -> SuccessResponse[UserRewardResponse]:
    result = await service.award_reward(user_id=user_id, data=body)
    return SuccessResponse(data=result, message="Reward awarded.")


async def activate_reward(
    reward_id: uuid.UUID,
    current_user: AdminDep,
    service: WalletServiceDep,
) -> SuccessResponse[UserRewardResponse]:
    result = await service.activate_reward(reward_id=reward_id, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Reward activated.")


async def redeem_reward(
    reward_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[UserRewardResponse]:
    result = await service.redeem_reward(reward_id=reward_id, user_id=current_user.id)
    return SuccessResponse(data=result, message="Reward redeemed.")


async def list_rewards(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: WalletServiceDep,
) -> CursorPaginatedResponse[UserRewardResponse]:
    page = await service.list_rewards(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def get_reward_balance(
    current_user: CurrentUserDep,
    service: WalletServiceDep,
) -> SuccessResponse[RewardBalanceResponse]:
    result = await service.get_reward_balance(user_id=current_user.id)
    return SuccessResponse(data=result, message="Reward balance retrieved.")
