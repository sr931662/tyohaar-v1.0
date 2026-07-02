"""widen packages.status column to support PENDING_REVIEW

Revision ID: a1b2c3d4e5f6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-02 00:00:00.000000

The initial schema created packages.status as VARCHAR(8), sized for the
longest original PackageStatus member (ARCHIVED / INACTIVE = 8 chars).
PENDING_REVIEW (14 chars) was added to PackageStatus after the schema was
created, so any UPDATE that sets status = 'PENDING_REVIEW' (i.e. a vendor
submitting a package for admin review) raises StringDataRightTruncationError.

Fix: widen the column to VARCHAR(50) so all current and future enum members fit.
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE packages "
        "ALTER COLUMN status TYPE VARCHAR(50)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE packages "
        "ALTER COLUMN status TYPE VARCHAR(8)"
    )
