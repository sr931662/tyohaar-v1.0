from __future__ import annotations

from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class NotificationNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Notification", identifier)


class NotificationOwnershipError(PermissionError):
    default_message = "You do not have permission to access this notification."


class TemplateNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("NotificationTemplate", identifier)


class TemplateKeyExistsError(ConflictError):
    default_message = "A template with this key already exists for the given channel and language."


class TemplateRenderError(ValidationError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, field)
