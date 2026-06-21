"""
Payments service package.

Import from here in routers and dependencies:
    from app.services.payments import PaymentService
"""

from __future__ import annotations

from app.services.payments.service import PaymentService

__all__ = ["PaymentService"]
