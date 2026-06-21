"""
Support domain — threaded customer support tickets, messages, and attachments.

Import order: SupportAttachment and SupportMessage first (leaf models),
then SupportTicket (root aggregate that owns them via cascade).
"""

from app.models.support.attachment import SupportAttachment, VirusScanStatus
from app.models.support.message import SupportMessage, SupportSenderRole, SupportMessageType
from app.models.support.ticket import SupportTicket

__all__ = [
    # Models
    "SupportTicket",
    "SupportMessage",
    "SupportAttachment",
    # Local enums (move to enums.py in next enums update)
    "SupportSenderRole",
    "SupportMessageType",
    "VirusScanStatus",
]
