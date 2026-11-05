"""Invitation management: event source, functions, households, per-function RSVP

Additive. Existing rows keep working unchanged: every celebration that already
has a booking becomes TYOHAAR_BOOKING linked to its earliest live booking, the
rest STANDALONE, and all stay PUBLISHED so links already shared don't go dark.
No guest row and no existing RSVP is rewritten.

Revision ID: e1a2b3c4d5f6
Revises: d5bca061fd0f
Create Date: 2026-11-05 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1a2b3c4d5f6"
down_revision: Union[str, None] = "d5bca061fd0f"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.alter_column("celebrations", "occasion_id", existing_type=UUID, nullable=True)

    for column in (
        sa.Column("event_source", sa.String(20), nullable=False, server_default="STANDALONE"),
        sa.Column("linked_booking_id", UUID, nullable=True),
        sa.Column("event_type", sa.String(40), nullable=True),
        sa.Column("custom_event_type", sa.String(80), nullable=True),
        sa.Column("host_name", sa.String(200), nullable=True),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column("cover_image_url", sa.String(1000), nullable=True),
        sa.Column("event_start_date", sa.Date(), nullable=True),
        sa.Column("event_end_date", sa.Date(), nullable=True),
        sa.Column("invitation_status", sa.String(20), nullable=False, server_default="PUBLISHED"),
        sa.Column("invitation_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invitation_settings", postgresql.JSONB(), nullable=True),
        sa.Column("general_link_hash", sa.String(64), nullable=True),
        sa.Column("general_link_enc", sa.Text(), nullable=True),
        sa.Column("general_link_visits", sa.Integer(), nullable=False, server_default="0"),
    ):
        op.add_column("celebrations", column)
    op.create_foreign_key(
        "fk_celebrations_linked_booking", "celebrations", "bookings",
        ["linked_booking_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "uq_celebrations_linked_booking", "celebrations", ["linked_booking_id"],
        unique=True, postgresql_where=sa.text("linked_booking_id IS NOT NULL"),
    )
    op.create_unique_constraint("uq_celebrations_general_link_hash", "celebrations", ["general_link_hash"])

    op.create_table(
        "celebration_functions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("celebration_id", UUID, sa.ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("function_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("venue_name", sa.String(300), nullable=True),
        sa.Column("venue_address", sa.Text(), nullable=True),
        sa.Column("map_url", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dress_code", sa.String(200), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("ix_celebration_functions_event", "celebration_functions", ["celebration_id", "display_order"])

    op.create_table(
        "celebration_guest_groups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("celebration_id", UUID, sa.ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("invitation_capacity", sa.SmallInteger(), nullable=True),
        sa.Column("response_mode", sa.String(20), nullable=False, server_default="GROUP"),
        sa.Column(
            "primary_guest_id", UUID,
            sa.ForeignKey("celebration_guests.id", ondelete="SET NULL", name="fk_guest_groups_primary_guest"),
            nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "invitation_capacity IS NULL OR invitation_capacity >= 1",
            name="ck_celebration_guest_groups_capacity",
        ),
    )
    op.create_index("ix_celebration_guest_groups_event", "celebration_guest_groups", ["celebration_id"])

    for column in (
        sa.Column("group_id", UUID, nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="host"),
        sa.Column("link_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rsvp_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
    ):
        op.add_column("celebration_guests", column)
    op.create_foreign_key(
        "fk_celebration_guests_group", "celebration_guests", "celebration_guest_groups",
        ["group_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_celebration_guests_group", "celebration_guests", ["group_id"])

    op.create_table(
        "guest_function_responses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("celebration_id", UUID, sa.ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("function_id", UUID, sa.ForeignKey("celebration_functions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("celebration_guest_id", UUID, sa.ForeignKey("celebration_guests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("attendee_count", sa.SmallInteger(), nullable=True),
        sa.Column("dietary_type", sa.String(30), nullable=True),
        sa.Column("meal_selection", sa.String(120), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("special_requirements", sa.Text(), nullable=True),
        sa.Column("answers", postgresql.JSONB(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("attendee_count IS NULL OR attendee_count >= 0", name="ck_guest_function_responses_attendees"),
    )
    op.create_index(
        "uq_guest_function_response", "guest_function_responses", ["celebration_guest_id", "function_id"],
        unique=True, postgresql_where=sa.text("function_id IS NOT NULL"),
    )
    op.create_index(
        "uq_guest_event_response", "guest_function_responses", ["celebration_guest_id"],
        unique=True, postgresql_where=sa.text("function_id IS NULL"),
    )
    op.create_index(
        "ix_guest_function_responses_event", "guest_function_responses", ["celebration_id", "function_id", "status"],
    )

    # Backfill: anything with a booking came through Tyohaar. Prefer a booking
    # that is still alive. DISTINCT ON picks one per celebration, and a booking
    # has exactly one celebration, so no booking can be linked twice.
    op.execute(
        """
        UPDATE celebrations c
        SET event_source = 'TYOHAAR_BOOKING', linked_booking_id = picked.id
        FROM (
            SELECT DISTINCT ON (celebration_id) celebration_id, id
            FROM bookings
            ORDER BY celebration_id,
                     (booking_status IN ('CANCELLED', 'REFUNDED')) ASC,
                     created_at ASC
        ) picked
        WHERE picked.celebration_id = c.id
        """
    )


def downgrade() -> None:
    op.drop_table("guest_function_responses")
    op.drop_index("ix_celebration_guests_group", table_name="celebration_guests")
    op.drop_constraint("fk_celebration_guests_group", "celebration_guests", type_="foreignkey")
    for name in (
        "group_id", "source", "link_accessed_at", "visit_count", "last_visited_at",
        "rsvp_started_at", "last_reminded_at", "reminder_count",
    ):
        op.drop_column("celebration_guests", name)
    op.drop_table("celebration_guest_groups")
    op.drop_table("celebration_functions")
    op.drop_constraint("uq_celebrations_general_link_hash", "celebrations", type_="unique")
    op.drop_index("uq_celebrations_linked_booking", table_name="celebrations")
    op.drop_constraint("fk_celebrations_linked_booking", "celebrations", type_="foreignkey")
    for name in (
        "event_source", "linked_booking_id", "event_type", "custom_event_type", "host_name",
        "contact_name", "contact_phone", "cover_image_url", "event_start_date", "event_end_date",
        "invitation_status", "invitation_published_at", "invitation_settings", "general_link_hash",
        "general_link_enc", "general_link_visits",
    ):
        op.drop_column("celebrations", name)
    # Independent events have no occasion, so this fails loudly if any exist;
    # silently inventing an occasion for them would be worse.
    op.alter_column("celebrations", "occasion_id", existing_type=UUID, nullable=False)
