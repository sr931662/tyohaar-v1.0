"""
Support domain — paginated list response schemas.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.support.response import SupportMessageResponse, SupportTicketResponse

__all__ = [
    "SupportTicketPage",
    "SupportMessagePage",
]

SupportTicketPage = CursorPage[SupportTicketResponse]
SupportMessagePage = CursorPage[SupportMessageResponse]
