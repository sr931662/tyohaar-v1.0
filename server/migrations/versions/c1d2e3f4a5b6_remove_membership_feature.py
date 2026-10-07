"""Remove the membership feature

Membership plans and subscriptions are gone from the product, so this drops
their tables and clears out every other row that only made sense with them.

Enum columns here are VARCHARs holding the Python enum member *name*
(SQLAlchemy's default for native_enum=False), so a row still holding a name
that no longer exists in app/models/enums.py would fail to load. Each such
value is therefore either remapped or removed before the code stops knowing it:

  * user_memberships, membership_plans      → dropped
  * coupons.eligible_membership_tiers       → dropped
  * coupons / package_discounts MEMBERSHIP_ONLY
                                            → archived/deactivated, then set
                                              to ALL so the value is gone
  * notifications about memberships         → deleted
  * notification templates MEMBERSHIP_EXPIRING → deleted
  * support tickets in MEMBERSHIP           → moved to GENERAL
  * FAQs in MEMBERSHIP                      → deleted
  * banners for PREMIUM_MEMBERS             → deactivated, audience CUSTOMERS
  * admin permissions on MEMBERSHIPS        → deleted (role links cascade)
  * automation rules on membership.* events → deleted; assign_membership
                                              actions stripped from the rest
  * app settings in the memberships group   → deleted

Kept on purpose: invoices with entity_type MEMBERSHIP (financial records that
must stay readable) and import logs for memberships (audit history).

Downgrade restores the dropped coupon column and the automation constraint
only. Membership tables and the deleted rows are not recreated — the data is
gone once this has run.

Revision ID: c1d2e3f4a5b6
Revises: 5d1bb478d45d
Create Date: 2026-10-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "5d1bb478d45d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRIGGERS_WITHOUT_MEMBERSHIP = (
    "'vendor.registered','vendor.approved','vendor.rejected',"
    "'booking.created','booking.confirmed','booking.completed','booking.cancelled',"
    "'payment.completed','payment.failed','payment.refunded',"
    "'user.registered','user.inactive','referral.completed',"
    "'support.ticket_opened','support.ticket_resolved'"
)
_TRIGGERS_WITH_MEMBERSHIP = (
    "'vendor.registered','vendor.approved','vendor.rejected',"
    "'booking.created','booking.confirmed','booking.completed','booking.cancelled',"
    "'payment.completed','payment.failed','payment.refunded',"
    "'membership.expiring','membership.expired','membership.renewed',"
    "'user.registered','user.inactive','referral.completed',"
    "'support.ticket_opened','support.ticket_resolved'"
)


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": name},
    ).fetchone() is not None


def _drop_trigger_check(table: str) -> None:
    # The constraint's real name depends on whether it was created by the
    # migration or by create_all() under the naming convention, so find it by
    # what it checks rather than by name.
    op.execute(
        f"""
        DO $$
        DECLARE c record;
        BEGIN
            FOR c IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'public.{table}'::regclass
                  AND contype = 'c'
                  AND pg_get_constraintdef(oid) LIKE '%trigger_event%'
            LOOP
                EXECUTE format('ALTER TABLE public.{table} DROP CONSTRAINT %I', c.conname);
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ── Membership tables ────────────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS user_memberships")
    op.execute("DROP TABLE IF EXISTS membership_plans")

    # ── Coupons and package discounts ────────────────────────────────────────
    if _table_exists(conn, "coupons"):
        op.execute(
            "UPDATE coupons SET admin_status = 'ARCHIVED', is_active = false, "
            "applicability = 'ALL' WHERE applicability = 'MEMBERSHIP_ONLY'"
        )
        op.execute("ALTER TABLE coupons DROP COLUMN IF EXISTS eligible_membership_tiers")
    if _table_exists(conn, "package_discounts"):
        op.execute(
            "UPDATE package_discounts SET is_active = false, applicability = 'ALL' "
            "WHERE applicability = 'MEMBERSHIP_ONLY'"
        )

    # ── Notifications ────────────────────────────────────────────────────────
    if _table_exists(conn, "notifications"):
        op.execute(
            "DELETE FROM notifications "
            "WHERE notification_type = 'MEMBERSHIP_EXPIRING' OR reference_type = 'membership'"
        )
    if _table_exists(conn, "notification_templates"):
        op.execute(
            "DELETE FROM notification_templates "
            "WHERE notification_category = 'MEMBERSHIP_EXPIRING'"
        )

    # ── Support, FAQs, banners ───────────────────────────────────────────────
    if _table_exists(conn, "support_tickets"):
        op.execute("UPDATE support_tickets SET category = 'GENERAL' WHERE category = 'MEMBERSHIP'")
    if _table_exists(conn, "faqs"):
        op.execute("DELETE FROM faqs WHERE faq_category = 'MEMBERSHIP'")
    if _table_exists(conn, "banners"):
        op.execute(
            "UPDATE banners SET is_active = false, target_audience = 'CUSTOMERS' "
            "WHERE target_audience = 'PREMIUM_MEMBERS'"
        )

    # ── Admin permissions ────────────────────────────────────────────────────
    if _table_exists(conn, "admin_permissions"):
        op.execute("DELETE FROM admin_permissions WHERE resource = 'MEMBERSHIPS'")

    # ── CMS automation ───────────────────────────────────────────────────────
    if _table_exists(conn, "cms_automation_rules"):
        op.execute("DELETE FROM cms_automation_rules WHERE trigger_event LIKE 'membership.%'")
        op.execute(
            """
            UPDATE cms_automation_rules
            SET actions = COALESCE(
                (SELECT jsonb_agg(a) FROM jsonb_array_elements(actions) a
                 WHERE a->>'type' IS DISTINCT FROM 'assign_membership'),
                '[]'::jsonb)
            WHERE jsonb_typeof(actions) = 'array'
              AND actions @> '[{"type": "assign_membership"}]'::jsonb
            """
        )
        _drop_trigger_check("cms_automation_rules")
        op.execute(
            "ALTER TABLE cms_automation_rules ADD CONSTRAINT ck_automation_rules_trigger_event "
            f"CHECK (trigger_event IN ({_TRIGGERS_WITHOUT_MEMBERSHIP}))"
        )

    # ── App settings ─────────────────────────────────────────────────────────
    if _table_exists(conn, "app_settings"):
        op.execute('DELETE FROM app_settings WHERE "group" = \'memberships\'')


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "cms_automation_rules"):
        _drop_trigger_check("cms_automation_rules")
        op.execute(
            "ALTER TABLE cms_automation_rules ADD CONSTRAINT ck_automation_rules_trigger_event "
            f"CHECK (trigger_event IN ({_TRIGGERS_WITH_MEMBERSHIP}))"
        )

    if _table_exists(conn, "coupons"):
        op.add_column(
            "coupons",
            sa.Column(
                "eligible_membership_tiers",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
