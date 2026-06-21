"""
Notifications domain schema package.

Single stable import entry point:

    from app.schemas.notifications import NotificationCreate, NotificationPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.notifications.common import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.notifications.create import (
    NotificationCreate,
    NotificationTemplateCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.notifications.update import (
    NotificationTemplateUpdate,
    NotificationUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.notifications.response import (
    NotificationResponse,
    NotificationTemplateResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.notifications.filters import (
    NotificationFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.notifications.pagination import (
    NotificationPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.notifications.internal import (
    NotificationBatchCreate,
    NotificationInternal,
)

__all__ = [
    # common
    "NotificationType",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationStatus",
    # create
    "NotificationCreate",
    "NotificationTemplateCreate",
    # update
    "NotificationUpdate",
    "NotificationTemplateUpdate",
    # response
    "NotificationResponse",
    "NotificationTemplateResponse",
    # filters
    "NotificationFilters",
    # pagination
    "NotificationPage",
    # internal
    "NotificationInternal",
    "NotificationBatchCreate",
]
