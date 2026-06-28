"""widen login_method columns to support EMAIL_PASSWORD

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-28 00:00:00.000000

The initial schema created primary_login_provider on users and login_method
on user_sessions as VARCHAR(9), sized for the longest original enum member
(OTP_PHONE / OTP_EMAIL = 9 chars).  EMAIL_PASSWORD (14 chars) was added to
LoginMethod after the schema was created, so any INSERT that sets
primary_login_provider = 'EMAIL_PASSWORD' raises StringDataRightTruncationError.

Fix: widen both columns to VARCHAR(50) so all current and future enum members fit.
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN primary_login_provider TYPE VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE user_sessions "
        "ALTER COLUMN login_method TYPE VARCHAR(50)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_sessions "
        "ALTER COLUMN login_method TYPE VARCHAR(9)"
    )
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN primary_login_provider TYPE VARCHAR(9)"
    )
