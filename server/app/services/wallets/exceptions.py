"""
Wallets domain exceptions.
"""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionError,
)


class WalletNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Wallet", identifier)


class WalletAlreadyExistsError(ConflictError):
    default_message = "A wallet already exists for this user."


class WalletFrozenError(BusinessRuleError):
    default_message = "Wallet is frozen and cannot process transactions."


class WalletSuspendedError(BusinessRuleError):
    default_message = "Wallet is suspended and cannot process transactions."


class WalletClosedError(BusinessRuleError):
    default_message = "Wallet is closed."


class WalletBalanceLimitError(BusinessRuleError):
    default_message = "Transaction would exceed the maximum wallet balance."


class RewardNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("UserReward", identifier)


class RewardAlreadyRedeemedError(ConflictError):
    default_message = "This reward has already been redeemed."


class RewardExpiredError(BusinessRuleError):
    default_message = "This reward has expired."


class WalletOwnershipError(PermissionError):
    default_message = "Wallet does not belong to this user."
