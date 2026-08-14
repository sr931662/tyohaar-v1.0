"""
Account deletion and data purge.

    service.py   — the lifecycle: request, deactivate, recover, purge
    runner.py    — executes registered handlers for one user
    registry.py  — the handler contract and tier ordering
    handlers/    — one module per domain
    backfill.py  — one-off resolution of Cloudinary ids for legacy media

Retention periods are not defined here. They live in `app/core/retention.py`
so a policy change never touches the engine.
"""

from app.services.deletion.service import DeletionService

__all__ = ["DeletionService"]
