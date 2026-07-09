"""
Feedback domain exceptions.
"""

from __future__ import annotations

from app.services.exceptions import NotFoundError


class FeedbackNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Feedback", identifier)
