"""add is_returnable to package_items

Revision ID: 77471ae03007
Revises: 7c3f648480e9
Create Date: 2026-07-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "77471ae03007"
down_revision = "7c3f648480e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_items",
        sa.Column("is_returnable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("package_items", "is_returnable")
