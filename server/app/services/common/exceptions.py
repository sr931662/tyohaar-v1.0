"""Common domain service exceptions."""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class StateNotFoundError(NotFoundError):
    """Raised when the requested State does not exist."""


class CityNotFoundError(NotFoundError):
    """Raised when the requested City does not exist."""


class StateHasCitiesError(ConflictError):
    """Raised when attempting to delete a State that still has cities."""


class CityBelongsToWrongStateError(ValidationError):
    """Raised when a City's state_id does not match the expected state."""


class BannerNotFoundError(NotFoundError):
    """Raised when the requested Banner does not exist."""


class ActiveBannerLimitError(BusinessRuleError):
    """Raised when activating a banner would exceed the maximum active banner count."""


class FAQNotFoundError(NotFoundError):
    """Raised when the requested FAQ does not exist."""


class AppSettingNotFoundError(NotFoundError):
    """Raised when the requested AppSetting key does not exist."""


class SystemSettingDeleteError(BusinessRuleError):
    """Raised when attempting to delete a system-critical (is_readonly) AppSetting."""


class TermsNotFoundError(NotFoundError):
    """Raised when no published Terms & Conditions version can be found."""


class PrivacyPolicyNotFoundError(NotFoundError):
    """Raised when no published Privacy Policy version can be found."""


class CancellationPolicyNotFoundError(NotFoundError):
    """Raised when no published Cancellation & Refund Policy version can be found."""
