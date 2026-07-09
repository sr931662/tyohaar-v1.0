"""
Occasions service — domain-specific exception types.
"""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionError,
)


class OccasionNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Occasion", identifier)


class CelebrationNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Celebration", identifier)


class CelebrationOwnershipError(PermissionError):
    default_message = "You do not have permission to modify this celebration."


class GuestLimitExceededError(BusinessRuleError):
    default_message = (
        "Guest limit reached. A celebration may have at most 500 guests."
    )


class GuestNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Guest", identifier)


class ChecklistLimitExceededError(BusinessRuleError):
    default_message = (
        "Checklist limit reached. A celebration may have at most 100 checklist items."
    )


class TimelineLimitExceededError(BusinessRuleError):
    default_message = (
        "Timeline limit reached. A celebration may have at most 50 timeline events."
    )
