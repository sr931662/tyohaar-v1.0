"""celebration guest history: append-only RSVP/invitation audit log

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "celebration_guest_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("celebration_guest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celebration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["celebration_guest_id"], ["celebration_guests.id"],
            name="fk_celebration_guest_history_guest_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["celebration_id"], ["celebrations.id"],
            name="fk_celebration_guest_history_celebration_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_celebration_guest_history_guest_id", "celebration_guest_history", ["celebration_guest_id"]
    )
    op.create_index(
        "ix_celebration_guest_history_celebration_id",
        "celebration_guest_history", ["celebration_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_celebration_guest_history_celebration_id", table_name="celebration_guest_history")
    op.drop_index("ix_celebration_guest_history_guest_id", table_name="celebration_guest_history")
    op.drop_table("celebration_guest_history")
