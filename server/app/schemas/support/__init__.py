"""
Support domain schema package.

Single stable import entry point:

    from app.schemas.support import SupportTicketCreate, SupportTicketResponse
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.support.common import (
    TicketCategory,
    TicketPriority,
    TicketSLAStatus,
    TicketStatus,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.support.create import (
    SupportAttachmentCreate,
    SupportMessageCreate,
    SupportTicketCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.support.update import (
    SupportMessageUpdate,
    SupportTicketAgentUpdate,
    SupportTicketUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.support.response import (
    SupportAttachmentResponse,
    SupportMessageResponse,
    SupportTicketAgentResponse,
    SupportTicketResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.support.filters import (
    SupportTicketFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.support.pagination import (
    SupportMessagePage,
    SupportTicketPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.support.internal import (
    SupportTicketAdminSummary,
    SupportTicketInternal,
)

__all__ = [
    # common
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketSLAStatus",
    # create
    "SupportTicketCreate",
    "SupportMessageCreate",
    "SupportAttachmentCreate",
    # update
    "SupportTicketUpdate",
    "SupportTicketAgentUpdate",
    "SupportMessageUpdate",
    # response
    "SupportTicketResponse",
    "SupportTicketAgentResponse",
    "SupportMessageResponse",
    "SupportAttachmentResponse",
    # filters
    "SupportTicketFilters",
    # pagination
    "SupportTicketPage",
    "SupportMessagePage",
    # internal
    "SupportTicketInternal",
    "SupportTicketAdminSummary",
]
