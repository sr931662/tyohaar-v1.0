"""add file_content/mime_type to cms_export_logs

Persists generated export bytes directly in Postgres (rather than a
public third-party file host) so they can be served through an
admin-authenticated download route without ever leaving the trust
boundary — exports can contain customer/payment PII.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cms_export_logs", sa.Column("file_content", sa.LargeBinary(), nullable=True))
    op.add_column("cms_export_logs", sa.Column("mime_type", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("cms_export_logs", "mime_type")
    op.drop_column("cms_export_logs", "file_content")
