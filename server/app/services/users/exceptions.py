from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)


class UserNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("User", identifier)


class PhoneTakenError(ConflictError):
    default_message = "A user with this phone number already exists."


class EmailTakenError(ConflictError):
    default_message = "A user with this email address already exists."


class AddressNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("UserAddress", identifier)


class AddressLimitExceededError(BusinessRuleError):
    default_message = "Maximum number of addresses per user has been reached."


class DeviceLimitExceededError(BusinessRuleError):
    default_message = "Maximum number of devices per user has been reached."
