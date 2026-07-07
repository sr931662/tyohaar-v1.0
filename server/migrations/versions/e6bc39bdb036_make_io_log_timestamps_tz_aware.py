"""make cms import/export log timestamps timezone-aware

Revision ID: e6bc39bdb036
Revises: 58c23f8b9659
Create Date: 2026-07-07 00:00:00.000000

cms_import_logs.started_at/completed_at and cms_export_logs.expires_at/
completed_at were declared as naive TIMESTAMP WITHOUT TIME ZONE, unlike
every other timestamp column in the app (which uses TIMESTAMP WITH TIME
ZONE via TimestampMixin). The service layer passes timezone-aware
datetime.now(tz=timezone.utc) values into these columns, which asyncpg
rejects outright ("can't subtract offset-naive and offset-aware
datetimes") — every import/export execution failed before this fix.
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = 'e6bc39bdb036'
down_revision: Union[str, None] = '58c23f8b9659'
branch_labels = None
depends_on = None

_COLUMNS = [
    ('cms_import_logs', 'started_at'),
    ('cms_import_logs', 'completed_at'),
    ('cms_export_logs', 'expires_at'),
    ('cms_export_logs', 'completed_at'),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE '
            f"USING {column} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE '
            f"USING {column} AT TIME ZONE 'UTC'"
        )
