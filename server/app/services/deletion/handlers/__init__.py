"""
Purge handlers.

Importing this package registers every handler with the registry. The runner
imports it once at startup; nothing else should need to import the individual
modules.

Execution order is set by each handler's tier, not by the import order below.
See `app/services/deletion/registry.py` for the tier constants and the
contract every handler honours.
"""

from app.services.deletion.handlers import (  # noqa: F401
    celebrations,
    content,
    external,
    guests,
    identity,
    media,
    relationships,
    support,
    transactional,
)

__all__ = [
    "celebrations",
    "content",
    "external",
    "guests",
    "identity",
    "media",
    "relationships",
    "support",
    "transactional",
]
