"""
Users Controller — user account, profile, addresses, and device management.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import UserServiceDep
from app.core.permissions import AdminDep, require_ownership
from app.core.responses import SuccessResponse
from app.schemas.users.create import UserAddressCreate, UserDeviceCreate
from app.schemas.users.response import (
    UserAddressResponse,
    UserDeviceResponse,
    UserProfileResponse,
    UserResponse,
)
from app.schemas.users.update import UserAddressUpdate, UserDeviceUpdate, UserProfileUpdate, UserUpdate
from app.services.users.service import UserFullResponse


async def get_me(
    current_user: CurrentUserDep,
) -> SuccessResponse[UserResponse]:
    return SuccessResponse(data=current_user, message="Profile retrieved.")


async def update_me(
    body: UserUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[UserResponse]:
    result = await service.update_user(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Profile updated.")


async def delete_me(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[None]:
    await service.deactivate_user(user_id=current_user.id)
    return SuccessResponse(data=None, message="Account deactivated.")


async def get_profile(
    user_id: uuid.UUID,
    _: Annotated[None, Depends(require_ownership("user_id"))],
    service: UserServiceDep,
) -> SuccessResponse[UserResponse]:
    result = await service.get_user(user_id=user_id)
    return SuccessResponse(data=result, message="User retrieved.")


async def update_profile(
    user_id: uuid.UUID,
    body: UserProfileUpdate,
    _: Annotated[None, Depends(require_ownership("user_id"))],
    service: UserServiceDep,
) -> SuccessResponse[UserProfileResponse]:
    result = await service.update_profile(user_id=user_id, data=body)
    return SuccessResponse(data=result, message="Profile updated.")


async def list_addresses(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[list[UserAddressResponse]]:
    addresses = await service.list_addresses(user_id=current_user.id)
    return SuccessResponse(data=addresses, message="Addresses retrieved.")


async def add_address(
    body: UserAddressCreate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[UserAddressResponse]:
    result = await service.add_address(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Address added.")


async def get_address(
    address_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[UserAddressResponse]:
    result = await service.get_address(user_id=current_user.id, address_id=address_id)
    return SuccessResponse(data=result, message="Address retrieved.")


async def update_address(
    address_id: uuid.UUID,
    body: UserAddressUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[UserAddressResponse]:
    result = await service.update_address(
        user_id=current_user.id, address_id=address_id, data=body
    )
    return SuccessResponse(data=result, message="Address updated.")


async def delete_address(
    address_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[None]:
    await service.delete_address(user_id=current_user.id, address_id=address_id)
    return SuccessResponse(data=None, message="Address deleted.")


async def list_devices(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[list[UserDeviceResponse]]:
    devices = await service.list_devices(user_id=current_user.id)
    return SuccessResponse(data=devices, message="Devices retrieved.")


async def register_device(
    body: UserDeviceCreate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[UserDeviceResponse]:
    result = await service.register_device(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Device registered.")


async def deactivate_device(
    device_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> SuccessResponse[None]:
    await service.deactivate_device(user_id=current_user.id, device_id=device_id)
    return SuccessResponse(data=None, message="Device deactivated.")


async def get_user_full(
    user_id: uuid.UUID,
    _admin: AdminDep,
    service: UserServiceDep,
) -> SuccessResponse[UserFullResponse]:
    result = await service.get_user_full(user_id=user_id)
    return SuccessResponse(data=result, message="Full user profile retrieved.")
