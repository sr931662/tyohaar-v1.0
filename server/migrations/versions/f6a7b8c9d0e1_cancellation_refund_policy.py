"""cancellation & refund policy: versioned CMS document

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cancellation_refund_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.Date(), nullable=True),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("must_accept_version", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"], ["cancellation_refund_policies.id"],
            name="fk_cancellation_refund_policies_superseded_by_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "version", "language",
            name="uq_cancellation_policies_version_language",
        ),
    )
    op.create_index(
        "ix_cancellation_policies_status", "cancellation_refund_policies", ["status"]
    )
    op.create_index(
        "ix_cancellation_policies_effective_date", "cancellation_refund_policies", ["effective_date"]
    )
    op.create_index(
        "ix_cancellation_policies_language", "cancellation_refund_policies", ["language"]
    )


def downgrade() -> None:
    op.drop_index("ix_cancellation_policies_language", table_name="cancellation_refund_policies")
    op.drop_index("ix_cancellation_policies_effective_date", table_name="cancellation_refund_policies")
    op.drop_index("ix_cancellation_policies_status", table_name="cancellation_refund_policies")
    op.drop_table("cancellation_refund_policies")
