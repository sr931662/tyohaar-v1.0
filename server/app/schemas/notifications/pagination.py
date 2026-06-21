"""
Notifications domain — paginated list response schemas.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.notifications.response import NotificationResponse

__all__ = [
    "NotificationPage",
]

NotificationPage = CursorPage[NotificationResponse]
