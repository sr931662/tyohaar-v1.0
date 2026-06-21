"""
Notifications domain — event-driven multi-channel notification delivery records.

Import order: NotificationTemplate first (Notification holds the FK to it).
"""

from app.models.notifications.template import NotificationTemplate
from app.models.notifications.notification import Notification

__all__ = [
    "NotificationTemplate",
    "Notification",
]
