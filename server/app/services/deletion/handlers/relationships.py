"""
Tier: relationships and platform records that survive in reduced form.

Three different treatments live here, and the distinction between them is the
whole point:

  * **Memberships** are deleted. The audit found no independent accounting
    value — every rupee lives in `payments`/`invoices`, which the membership
    merely points at — and nothing in the schema references the table.

  * **Referrals** are reduced to counters. Fraud and reward accounting need to
    know that a reward was earned and paid, not who the two parties were, and
    certainly not their IP address or device fingerprint.

  * **Reviews** and **audit logs** keep pointing at the tombstone. That is
    pseudonymisation, not anonymisation, and it is described as such
    everywhere it appears. The review strategy is configurable because the
    choice between severing authorship entirely and keeping the tombstone link
    is a business decision, not a technical one.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.retention import (
    REVIEW_AUTHOR_STRATEGY,
    SCRUB_REVIEW_FREE_TEXT,
)
from app.models.memberships.user_membership import UserMembership
from app.models.packages.package_item_review import PackageItemReview
from app.models.packages.package_review import PackageReview
from app.models.referrals.referral import Referral
from app.models.referrals.referral_milestone import ReferralMilestoneGrant
from app.models.vendors.vendor_review import VendorReview
from app.services.deletion.registry import (
    TIER_SANITISE,
    PurgeReport,
    register_purge,
)

# Contact details customers write into review bodies. Conservative on purpose:
# these patterns only match things that are unambiguously an email or an Indian
# mobile number, so ordinary prose survives untouched.
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_PHONE_RE = re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b")
_REDACTED = "[removed]"

_REVIEW_MODELS = (
    (PackageReview, "package_reviews"),
    (PackageItemReview, "package_item_reviews"),
    (VendorReview, "vendor_reviews"),
)


def _scrub(text: str | None) -> str | None:
    if not text:
        return text
    return _PHONE_RE.sub(_REDACTED, _EMAIL_RE.sub(_REDACTED, text))


@register_purge("memberships", order=TIER_SANITISE)
async def purge_memberships(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Delete membership rows outright.

    Reclassified from RETAIN during the field-level audit: the table holds
    platform state and free text (`cancellation_notes`, `upgrade_reason`,
    `renewal_history`) and no accounting record of its own.
    """
    report = PurgeReport(handler="memberships")

    result = await session.execute(
        delete(UserMembership).where(UserMembership.user_id == user_id)
    )
    report.count("user_memberships", result.rowcount or 0)

    return report


@register_purge("referrals", order=TIER_SANITISE + 10)
async def purge_referrals(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Reduce referral records to the minimum needed for reward accounting."""
    report = PurgeReport(handler="referrals")

    # Milestone grants are per-user progress counters with no accounting role
    # once the reward itself is recorded.
    result = await session.execute(
        delete(ReferralMilestoneGrant).where(
            ReferralMilestoneGrant.user_id == user_id
        )
    )
    report.count("referral_milestone_grants", result.rowcount or 0)

    # Anti-fraud telemetry is personal data in its own right — an IP address
    # and a device fingerprint identify a person as surely as a phone number,
    # and neither is needed once the referral has been settled.
    sanitised = {
        "ip_address": None,
        "device_fingerprint": None,
        "fraud_detection_reason": None,
        "attribution": None,
    }

    result = await session.execute(
        update(Referral)
        .where(Referral.referrer_id == user_id)
        .values(**sanitised)
    )
    report.count("referrals_as_referrer_sanitised", result.rowcount or 0)

    # Sever the referee side, which the FK permits. What survives is "a
    # referral existed and paid out", not "these two people know each other".
    result = await session.execute(
        update(Referral)
        .where(Referral.referred_user_id == user_id)
        .values(referred_user_id=None, **sanitised)
    )
    report.count("referrals_as_referee_cleared", result.rowcount or 0)

    # `referral_code` is NOT NULL and cannot be cleared. It is a generated
    # token, not a personal identifier, but it is a durable handle that an
    # out-of-band record could match back — flagged rather than hidden.
    report.defer(
        "referral_code retained (NOT NULL); generated token, resolves only to "
        "the tombstone user"
    )

    return report


@register_purge("reviews", order=TIER_SANITISE + 20)
async def purge_reviews(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Handle review authorship per the configured strategy.

    All three review tables hold RESTRICT/NOT NULL foreign keys to `users`, so
    the author column cannot simply be nulled. The strategy decides what
    happens instead; the free-text scrub happens regardless, because a review
    body containing "call me on 98…" leaks contact details no matter who the
    author column points at.
    """
    report = PurgeReport(handler="reviews")

    if SCRUB_REVIEW_FREE_TEXT:
        for model, label in _REVIEW_MODELS:
            rows = (
                (
                    await session.execute(
                        select(model.id, model.title, model.body).where(
                            model.customer_id == user_id
                        )
                    )
                )
                .tuples()
                .all()
            )
            scrubbed = 0
            for row_id, title, body in rows:
                new_title, new_body = _scrub(title), _scrub(body)
                if new_title != title or new_body != body:
                    await session.execute(
                        update(model)
                        .where(model.id == row_id)
                        .values(title=new_title, body=new_body)
                    )
                    scrubbed += 1
            report.count(f"{label}_text_scrubbed", scrubbed)

    if REVIEW_AUTHOR_STRATEGY == "purge":
        for model, label in _REVIEW_MODELS:
            result = await session.execute(
                delete(model).where(model.customer_id == user_id)
            )
            report.count(f"{label}_deleted", result.rowcount or 0)

    elif REVIEW_AUTHOR_STRATEGY == "sentinel":
        # Requires a provisioned sentinel user. Until one exists this would
        # silently do nothing, so it is reported rather than assumed done.
        report.defer(
            "sentinel strategy selected but no sentinel user is provisioned; "
            "authorship still points at the tombstone"
        )

    else:  # "tombstone" — the default, and the reversible option
        report.defer(
            "author reference retained on the tombstone user "
            "(pseudonymised, not anonymised) — pending client decision"
        )

    return report


@register_purge("audit_logs", order=TIER_SANITISE + 30)
async def purge_audit_logs(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Leave the security audit trail intact, pseudonymised.

    An audit trail the subject of the audit can erase is not an audit trail.
    `audit_logs.actor_id` is a bare UUID with no foreign key, so it survives
    the tombstone naturally. Nothing is deleted here; the entry exists so that
    the deliberate retention appears in the compliance report rather than
    looking like an oversight.
    """
    report = PurgeReport(handler="audit_logs")
    report.defer(
        "audit actor retained as tombstone id (pseudonymised, by design) — "
        "expires on AUDIT_LOG_RETENTION_DAYS"
    )
    return report
