"""fix otp_records schema drift: add failure_reason, delivered_at, delivery_reference

The OTPRecord model declares failure_reason/delivered_at/delivery_reference
but the original auth-tables migration only ever created failure_log --
these three columns were added to the model later without a matching
migration, so every OTP creation (any channel) has been failing with
UndefinedColumnError in production.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("otp_records", sa.Column("failure_reason", sa.String(length=200), nullable=True))
    op.add_column("otp_records", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("otp_records", sa.Column("delivery_reference", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("otp_records", "delivery_reference")
    op.drop_column("otp_records", "delivered_at")
    op.drop_column("otp_records", "failure_reason")
