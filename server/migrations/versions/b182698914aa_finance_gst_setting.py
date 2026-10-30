"""finance.gst_enabled app setting — GST becomes an admin switch, off by default

GST used to be hard-wired at 18% on every booking. It is now charged only while
the admin's Settings → Finance switch is on, stored as the `finance.gst_enabled`
row in app_settings.

The row is seeded OFF. `ON CONFLICT DO NOTHING` means re-running, or a row an
admin already created, is never overwritten. Existing bookings are untouched:
they keep the tax_amount they were created with.

The enum column stores the member *name*, hence 'BOOLEAN'.

Revision ID: b182698914aa
Revises: a0b1c2d3e4f6
Create Date: 2026-10-30 00:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b182698914aa"
down_revision: Union[str, None] = "a0b1c2d3e4f6"
branch_labels = None
depends_on = None

KEY = "finance.gst_enabled"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO app_settings
                (id, key, "group", label, description, value, default_value, data_type,
                 is_sensitive, is_readonly, is_environment_specific, is_active)
            VALUES
                (:id, :key, 'finance', 'Charge GST on bookings', :description,
                 'false', 'false', 'BOOLEAN', false, false, false, true)
            ON CONFLICT (key) DO NOTHING
            """
        ).bindparams(
            id=uuid.uuid4(),
            key=KEY,
            description=(
                "When on, 18% GST is added to new bookings on the post-discount amount. "
                "When off, no tax is charged or shown. Existing bookings keep their amounts."
            ),
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM app_settings WHERE key = :key").bindparams(key=KEY))
