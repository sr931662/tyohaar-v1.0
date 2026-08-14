"""account deletion pipeline: deletion_requests, media object ids, unresolved assets

Revision ID: 9b2e8c4d3f51
Revises: 9a1f7b3c2d40
Create Date: 2026-08-14

Additive only. No column is dropped and no data is destroyed by this
migration — the new media identifier columns are nullable and populated by a
separate, resumable backfill (app/services/deletion/backfill.py) so that a
long-running scan never blocks a deploy.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9b2e8c4d3f51'
down_revision: Union[str, None] = '9a1f7b3c2d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── deletion_requests ─────────────────────────────────────────────────────
    op.create_table(
        "deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("identifier_hash", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovery_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_hold_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_hold_reason", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("purge_report", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # SET NULL, not CASCADE: the compliance record must outlive the user.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_deletion_requests_due",
        "deletion_requests",
        ["status", "recovery_ends_at"],
    )
    op.create_index("ix_deletion_requests_user_id", "deletion_requests", ["user_id"])
    op.create_index(
        "ix_deletion_requests_identifier_hash",
        "deletion_requests",
        ["identifier_hash"],
    )
    # One live request per user. Completed/cancelled rows are excluded so a
    # user who cancels can request deletion again later.
    #
    # The literals are the enum MEMBER NAMES, not their values. SQLAlchemy's
    # Enum type persists `.name` by default, so DeletionRequestStatus.RECOVERABLE
    # is stored as 'RECOVERABLE' — a predicate written against the lowercase
    # `.value` would match nothing and the constraint would silently never fire.
    op.create_index(
        "uq_deletion_requests_active_user",
        "deletion_requests",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('PENDING_VERIFICATION', 'RECOVERABLE', 'PURGING')"
        ),
    )

    # ── media object identifiers ──────────────────────────────────────────────
    for table in ("images", "videos"):
        op.add_column(
            table,
            sa.Column("storage_public_id", sa.String(500), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("storage_provider", sa.String(50), nullable=True),
        )
        op.create_index(
            f"ix_{table}_storage_public_id", table, ["storage_public_id"]
        )

    op.add_column(
        "user_profiles",
        sa.Column("profile_photo_public_id", sa.String(500), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("cover_image_public_id", sa.String(500), nullable=True),
    )

    # ── unresolved_media_assets ───────────────────────────────────────────────
    op.create_table(
        "unresolved_media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_kind", sa.String(30), nullable=False),
        # No FK by design — this row must survive its source being removed.
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "media_kind", "media_id", name="uq_unresolved_media_assets_kind_id"
        ),
    )
    op.create_index(
        "ix_unresolved_media_assets_owner_id", "unresolved_media_assets", ["owner_id"]
    )
    op.create_index(
        "ix_unresolved_media_assets_resolved_at",
        "unresolved_media_assets",
        ["resolved_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_unresolved_media_assets_resolved_at", table_name="unresolved_media_assets"
    )
    op.drop_index(
        "ix_unresolved_media_assets_owner_id", table_name="unresolved_media_assets"
    )
    op.drop_table("unresolved_media_assets")

    op.drop_column("user_profiles", "cover_image_public_id")
    op.drop_column("user_profiles", "profile_photo_public_id")

    for table in ("images", "videos"):
        op.drop_index(f"ix_{table}_storage_public_id", table_name=table)
        op.drop_column(table, "storage_provider")
        op.drop_column(table, "storage_public_id")

    op.drop_index("uq_deletion_requests_active_user", table_name="deletion_requests")
    op.drop_index(
        "ix_deletion_requests_identifier_hash", table_name="deletion_requests"
    )
    op.drop_index("ix_deletion_requests_user_id", table_name="deletion_requests")
    op.drop_index("ix_deletion_requests_due", table_name="deletion_requests")
    op.drop_table("deletion_requests")
