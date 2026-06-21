"""
Repository layer — data access objects for all Tyohaar domains.

The public surface area is:
    - UnitOfWork: the transactional context manager; start here.
    - BaseRepository / Page: base types for extending or typing repositories.
    - Exception classes: NotFoundError, AlreadyExistsError, etc.

Domain repositories are exposed through UnitOfWork properties, not imported directly.
"""

from app.repositories.base import (
    AlreadyExistsError,
    BaseRepository,
    DatabaseError,
    NotFoundError,
    Page,
    RepositoryError,
    StaleDataError,
)
from app.repositories.unit_of_work import UnitOfWork

__all__ = [
    "UnitOfWork",
    "BaseRepository",
    "Page",
    "RepositoryError",
    "NotFoundError",
    "AlreadyExistsError",
    "StaleDataError",
    "DatabaseError",
]
