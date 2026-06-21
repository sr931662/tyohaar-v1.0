from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionError,
)


class TicketNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("SupportTicket", identifier)


class TicketOwnershipError(PermissionError):
    default_message = "You do not have permission to access this ticket."


class TicketClosedError(BusinessRuleError):
    default_message = "Cannot add messages to a closed ticket."


class TicketStatusTransitionError(BusinessRuleError):
    default_message = "This status transition is not allowed."


class OpenTicketLimitError(BusinessRuleError):
    default_message = "You have reached the maximum number of open support tickets."


class MessageNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("SupportMessage", identifier)


class AttachmentNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("SupportAttachment", identifier)


class AttachmentLimitError(BusinessRuleError):
    default_message = "Maximum number of attachments per message reached."
