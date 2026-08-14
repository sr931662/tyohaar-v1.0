"""
Data retention configuration — the single source of truth for every period
the deletion and purge pipeline observes.

Nothing in the purge engine reads a hardcoded duration. Every value lives
here so a policy change is a one-line edit and never a redesign.

Two classes of value live in this module and they are NOT interchangeable:

  * Product/operational periods — decided by Tyohaar, documented with their
    business reason, changeable at will.

  * Statutory periods — these carry a `*_CONFIRMED` flag that is False until
    the client's counsel signs off on both the duration and its legal basis.
    While a flag is False the pipeline *refuses to purge* the data it guards.
    That is the safe failure direction: we never destroy a record that might
    be legally required, and we never claim to have deleted one.

No period in this module asserts a legal requirement. Where a duration is
labelled statutory it is a placeholder awaiting confirmation, not advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

# ── Deletion lifecycle (product policy) ───────────────────────────────────────

#: Days between a verified deletion request and the point at which the account
#: stops being restorable. During this window the account is deactivated and
#: invisible but nothing has been destroyed.
RECOVERY_WINDOW_DAYS = 14

#: Outer SLA, measured from the verified request, by which the purge must have
#: completed. The daily job targets anything past the recovery window; this
#: value exists so overdue requests can be surfaced and alerted on.
PURGE_DEADLINE_DAYS = 30


# ── Third-party guest PII (product policy, event-anchored) ────────────────────

#: How long invitation/celebration guest contact details survive *after the
#: event they belong to*. 548 days ≈ 18 months.
#:
#: Business reason: the dominant reuse pattern on Tyohaar is a host reusing
#: last year's guest list for the same recurring occasion — Diwali to Diwali,
#: one anniversary to the next. A window under 12 months breaks that for a
#: host planning even slightly early; 18 months covers one full annual cycle
#: plus planning slack and then expires.
#:
#: This is a product retention decision. It carries no statutory claim.
#:
#: The clock is anchored to the event date, never to the host's account age,
#: so it runs identically whether or not the host is still a user.
GUEST_PII_AFTER_EVENT_DAYS = 548


# ── Operational (product policy) ──────────────────────────────────────────────

#: Idle days after which a device registration and its push token are dropped.
#: Independent of any deletion request — a stale token is a live notification
#: path to a device the user may no longer own.
DEVICE_TOKEN_IDLE_DAYS = 90


# ── Security (product policy, review annually) ────────────────────────────────

#: How long the salted hash of a banned user's identifiers is kept so a ban
#: survives account deletion. Only a keyed hash is stored — never the raw
#: phone or email — so this cannot be reversed into contact details.
ABUSE_HASH_RETENTION_DAYS = 1095  # 3 years

#: Admin audit trail. Pseudonymised, not anonymised: the actor is reduced to
#: the tombstone user id, which remains joinable to retained records. An audit
#: trail the subject of the audit can erase is not an audit trail.
AUDIT_LOG_RETENTION_DAYS = 730  # 2 years


# ── Periods awaiting counsel confirmation ─────────────────────────────────────
#
# Each guarded period pairs a duration with a confirmation flag. While the
# flag is False, `guarded_period()` returns None and every caller treats that
# as "retain indefinitely, purge nothing, claim nothing".


@dataclass(frozen=True)
class GuardedPeriod:
    """A retention period that is not usable until counsel confirms it.

    `days` is a placeholder. `confirmed` gates whether the pipeline may act
    on it at all. `note` records exactly what has to be answered so the
    open question travels with the value instead of living in a document
    nobody reads.
    """

    days: int
    confirmed: bool
    note: str

    @property
    def delta(self) -> timedelta | None:
        """The period as a timedelta, or None while unconfirmed."""
        return timedelta(days=self.days) if self.confirmed else None

    def __bool__(self) -> bool:
        return self.confirmed


#: Financial and tax records (invoices, booking invoices, payments, refunds,
#: transactions). Placeholder only.
#:
#: PENDING COUNSEL: the correct duration and its statutory basis.
#: Until confirmed, financial records are never purged.
FINANCIAL_RECORD_RETENTION = GuardedPeriod(
    days=2920,  # ~8 years, placeholder
    confirmed=False,
    note=(
        "Retention duration and statutory basis for financial/tax records "
        "must be confirmed by the client's counsel."
    ),
)

#: Evidence that a deletion request was made and honoured. Placeholder only.
#:
#: PENDING COUNSEL: how long proof-of-compliance must be retained.
#: Until confirmed, deletion evidence is never purged — which is the safe
#: direction, since this record is what protects Tyohaar in a dispute.
DELETION_EVIDENCE_RETENTION = GuardedPeriod(
    days=2555,  # ~7 years, placeholder
    confirmed=False,
    note=(
        "Retention duration for deletion-request evidence must be confirmed "
        "by the client's counsel."
    ),
)


# ── Invoice field sanitisation (pending counsel) ──────────────────────────────
#
# The purge engine supports field-level sanitisation of retained invoices, but
# it will not act on any field whose necessity is unresolved. These two sets
# are the whole control surface: move a field from PENDING to SCRUBBABLE once
# counsel confirms it is not required, and the next purge starts clearing it.
# No other code changes.

#: Fields on retained invoices that are confirmed NOT required for the
#: financial/tax purpose and may be cleared at purge time.
#:
#: Empty until counsel rules. Deliberately not pre-populated with guesses.
INVOICE_SCRUBBABLE_FIELDS: frozenset[str] = frozenset()

#: Fields whose necessity is unresolved. These are left exactly as-is and no
#: privacy claim may be published about them.
#:
#: PENDING COUNSEL: which of these are legally required on a retained tax
#: invoice, and which may move into INVOICE_SCRUBBABLE_FIELDS above.
INVOICE_PENDING_COUNSEL_FIELDS: frozenset[str] = frozenset(
    {
        "billing_name",
        "billing_address",
        "billing_city",
        "billing_state",
        "billing_pincode",
        "billing_gstin",
        "billing_pan",
        "billing_email",
        "billing_phone",
    }
)

#: Keys inside `invoices.billing_snapshot` (JSONB) mirroring the above.
INVOICE_SNAPSHOT_SCRUBBABLE_KEYS: frozenset[str] = frozenset()
INVOICE_SNAPSHOT_PENDING_COUNSEL_KEYS: frozenset[str] = frozenset(
    {"name", "email", "phone", "address", "gstin", "pan"}
)


# ── Invoice PDF handling (pending client) ─────────────────────────────────────

#: Whether generated invoice PDFs are deleted from storage when a customer is
#: purged. A stored PDF renders the same billing details as the database row,
#: so leaving it in place makes any field-level sanitisation cosmetic.
#:
#: PENDING CLIENT: deleting these changes how historical invoices are served
#: (they would need regenerating on demand). Default False = keep the current
#: working behaviour and make no deletion claim about PDFs.
PURGE_INVOICE_PDFS = False


# ── Review authorship (pending client) ────────────────────────────────────────

#: How a deleted user's reviews are handled.
#:
#:   "tombstone" — the review keeps pointing at the emptied user row. The link
#:                 survives; this is pseudonymisation, not anonymisation.
#:   "sentinel"  — every deleted author is repointed at one shared sentinel
#:                 user, severing the link entirely. Stronger privacy, but
#:                 per-person traceability is lost permanently.
#:   "purge"     — the review row is deleted with the user. Changes vendor
#:                 rating history.
#:
#: PENDING CLIENT. Default "tombstone" is the current, reversible behaviour:
#: it destroys nothing, so either other option can still be applied later.
REVIEW_AUTHOR_STRATEGY = "tombstone"

#: Phone/email patterns are stripped from review bodies regardless of the
#: strategy above — customers routinely write contact details into reviews.
SCRUB_REVIEW_FREE_TEXT = True


# ── Backups (deployment check) ────────────────────────────────────────────────

#: Days a Cloud SQL automated backup / PITR window may still contain purged
#: rows. None means "not yet verified against the production project".
#:
#: DEPLOYMENT CHECK: read the real value from the Cloud SQL instance and set
#: it here. No public statement about the purge horizon may be made while this
#: is None — see `backup_horizon_statement()`.
BACKUP_RETENTION_DAYS: int | None = None


def backup_horizon_statement() -> str:
    """Return the only sentence we are entitled to publish about backups."""
    if BACKUP_RETENTION_DAYS is None:
        return (
            "Purged records may persist in encrypted database backups until "
            "those backups age out on their normal rotation."
        )
    return (
        "Purged records may persist in encrypted database backups for up to "
        f"{BACKUP_RETENTION_DAYS} days, after which those backups age out."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

RECOVERY_WINDOW = timedelta(days=RECOVERY_WINDOW_DAYS)
PURGE_DEADLINE = timedelta(days=PURGE_DEADLINE_DAYS)
GUEST_PII_AFTER_EVENT = timedelta(days=GUEST_PII_AFTER_EVENT_DAYS)


def unconfirmed_periods() -> list[tuple[str, GuardedPeriod]]:
    """Every guarded period still awaiting counsel, for startup logging."""
    return [
        (name, period)
        for name, period in (
            ("FINANCIAL_RECORD_RETENTION", FINANCIAL_RECORD_RETENTION),
            ("DELETION_EVIDENCE_RETENTION", DELETION_EVIDENCE_RETENTION),
        )
        if not period.confirmed
    ]
