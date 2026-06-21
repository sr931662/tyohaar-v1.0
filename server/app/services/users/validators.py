"""
Async validators for the users service domain.
"""

from __future__ import annotations

import uuid

from app.models.users.address import UserAddress
from app.repositories.unit_of_work import UnitOfWork
from app.services.users.constants import MAX_ADDRESSES_PER_USER, MAX_DEVICES_PER_USER
from app.services.users.exceptions import (
    AddressLimitExceededError,
    AddressNotFoundError,
    DeviceLimitExceededError,
    EmailTakenError,
    PhoneTakenError,
)


async def validate_phone_unique(
    phone: str,
    uow: UnitOfWork,
    exclude_user_id: uuid.UUID | None = None,
) -> None:
    """
    Raise PhoneTakenError if *phone* is already registered to a different user.
    Pass *exclude_user_id* to allow the current user's own phone through (update path).
    """
    existing = await uow.users.users.find_by_phone(phone)
    if existing is not None:
        if exclude_user_id is None or existing.id != exclude_user_id:
            raise PhoneTakenError(f"Phone number {phone} is already in use.")


async def validate_email_unique(
    email: str,
    uow: UnitOfWork,
    exclude_user_id: uuid.UUID | None = None,
) -> None:
    """
    Raise EmailTakenError if *email* is already registered to a different user.
    """
    existing = await uow.users.users.find_by_email(email)
    if existing is not None:
        if exclude_user_id is None or existing.id != exclude_user_id:
            raise EmailTakenError(f"Email address {email} is already in use.")


async def validate_address_limit(
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    """Raise AddressLimitExceededError if the user already has MAX_ADDRESSES_PER_USER."""
    count = await uow.users.addresses.count(UserAddress.user_id == user_id)
    if count >= MAX_ADDRESSES_PER_USER:
        raise AddressLimitExceededError(
            f"Cannot add more than {MAX_ADDRESSES_PER_USER} addresses per user."
        )


async def validate_address_ownership(
    address_id: uuid.UUID,
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> UserAddress:
    """
    Fetch the address and verify it belongs to *user_id*.

    Raises:
        AddressNotFoundError: if address does not exist or belongs to another user.
    """
    address = await uow.users.addresses.get_by_id(address_id)
    if address is None or address.user_id != user_id:
        raise AddressNotFoundError(str(address_id))
    return address


async def validate_device_limit(
    user_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    """Raise DeviceLimitExceededError if the user already has MAX_DEVICES_PER_USER."""
    from app.models.users.device import UserDevice

    count = await uow.users.devices.count(UserDevice.user_id == user_id)
    if count >= MAX_DEVICES_PER_USER:
        raise DeviceLimitExceededError(
            f"Cannot register more than {MAX_DEVICES_PER_USER} devices per user."
        )
