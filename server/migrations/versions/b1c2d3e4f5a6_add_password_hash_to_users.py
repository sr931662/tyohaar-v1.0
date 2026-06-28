"""add password_hash to users

Revision ID: b1c2d3e4f5a6
Revises: a3f8c21e9b04
Create Date: 2026-06-28 00:00:00.000000

"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a3f8c21e9b04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
    )


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
