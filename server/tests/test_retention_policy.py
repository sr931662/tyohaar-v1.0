"""
Retention policy guards.

These tests defend the promises the product makes in public. Most of them fail
loudly if someone later takes a shortcut that would turn a truthful statement
into a false one — an unverified legal period quietly enabled, an inactivity
purge added, a claim published about data that is still retained.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core import retention

SERVER_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = SERVER_ROOT / "app"


# ── Guarded (counsel-pending) periods ─────────────────────────────────────────


def test_statutory_periods_ship_unconfirmed():
    """No legal duration is asserted without sign-off.

    If this test fails, someone flipped a `confirmed` flag. That is a legal
    decision, not a code change, and it must arrive with counsel's answer.
    """
    assert retention.FINANCIAL_RECORD_RETENTION.confirmed is False
    assert retention.DELETION_EVIDENCE_RETENTION.confirmed is False


def test_unconfirmed_period_refuses_to_produce_a_deadline():
    """An unconfirmed period yields no timedelta, so nothing can act on it."""
    assert retention.FINANCIAL_RECORD_RETENTION.delta is None
    assert not retention.FINANCIAL_RECORD_RETENTION

    confirmed = retention.GuardedPeriod(days=30, confirmed=True, note="x")
    assert confirmed.delta is not None
    assert confirmed


def test_unconfirmed_periods_are_enumerable_for_startup_logging():
    names = [name for name, _ in retention.unconfirmed_periods()]
    assert "FINANCIAL_RECORD_RETENTION" in names
    assert "DELETION_EVIDENCE_RETENTION" in names


# ── Invoice field sanitisation ────────────────────────────────────────────────


def test_invoice_fields_pending_counsel_are_not_also_scrubbable():
    """A field cannot be both 'unresolved' and 'safe to clear'."""
    overlap = (
        retention.INVOICE_SCRUBBABLE_FIELDS & retention.INVOICE_PENDING_COUNSEL_FIELDS
    )
    assert not overlap, f"contradictory classification for: {overlap}"

    snapshot_overlap = (
        retention.INVOICE_SNAPSHOT_SCRUBBABLE_KEYS
        & retention.INVOICE_SNAPSHOT_PENDING_COUNSEL_KEYS
    )
    assert not snapshot_overlap


def test_sensitive_invoice_identifiers_are_still_pending():
    """PAN and contact details must not be silently reclassified.

    Moving these into SCRUBBABLE is exactly the right change to make once
    counsel rules — this test exists so that change is deliberate and visible
    in review rather than incidental.
    """
    for field in ("billing_pan", "billing_email", "billing_phone"):
        assert field in retention.INVOICE_PENDING_COUNSEL_FIELDS


# ── Backup honesty ────────────────────────────────────────────────────────────


def test_backup_statement_makes_no_promise_without_a_verified_window():
    """With no verified rotation window, we may not quote a number."""
    assert retention.BACKUP_RETENTION_DAYS is None, (
        "once the real Cloud SQL window is known, set it here and update this "
        "test to assert the published number"
    )
    statement = retention.backup_horizon_statement()
    assert not re.search(r"\d+\s*days", statement), (
        "the published backup statement quoted a duration that has not been "
        "verified against the production instance"
    )


# ── No inactivity deletion, anywhere ──────────────────────────────────────────


DELETION_ROOT = APP_ROOT / "services" / "deletion"
JOBS_ROOT = APP_ROOT / "jobs"


def _deletion_pipeline_sources() -> list[Path]:
    """Every module that can actually destroy account data on a schedule.

    Scoped deliberately. A broad scan of the whole app produces noise —
    analytics counts daily actives with `last_login_at`, admin tooling has a
    bulk soft-delete — none of which is an automatic inactivity purge. What
    matters is that no *unattended* path deletes an account for being idle,
    and those paths all live in these two packages.
    """
    return [
        p
        for root in (DELETION_ROOT, JOBS_ROOT)
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    ]


def test_deletion_pipeline_never_keys_on_activity():
    """Dormancy must never trigger deletion.

    Tyohaar users routinely disappear for a year or more between celebrations.
    An inactivity purge would destroy real accounts belonging to people who
    are simply between events.
    """
    activity_columns = re.compile(
        r"(last_login_at|last_active_at|is_active\s*==\s*False|AccountStatus\.INACTIVE)"
    )

    offenders: list[str] = []
    for path in _deletion_pipeline_sources():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            # Comments and docstring prose describe the absence of the rule.
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            # The tombstone legitimately *clears* last_login_at; that is
            # erasure of an activity trace, not a trigger keyed on one.
            if "last_login_at=None" in stripped:
                continue
            if activity_columns.search(stripped):
                offenders.append(
                    f"{path.relative_to(SERVER_ROOT)}:{lineno}: {stripped[:100]}"
                )

    assert not offenders, (
        "the deletion pipeline referenced an activity column — deletion must "
        "be driven only by an explicit request:\n" + "\n".join(offenders)
    )


def test_purge_selection_is_driven_by_the_request_clock():
    """`find_due` must select on the recovery window, nothing else."""
    source = (DELETION_ROOT / "service.py").read_text(encoding="utf-8")
    find_due = source.split("async def find_due")[1].split("async def")[0]

    assert "DeletionRequest.recovery_ends_at <= now" in find_due
    assert "legal_hold_until" in find_due, (
        "a purge must be suspendable by legal hold"
    )
    assert "last_login" not in find_due
    assert "User." not in find_due, (
        "due-ness is a property of the request, never of the user's activity"
    )


def test_device_token_idle_expiry_is_operational_not_account_deletion():
    """Idle *tokens* expire; idle *accounts* do not.

    These are easy to conflate. The device window is short precisely because
    it does not touch the account.
    """
    assert retention.DEVICE_TOKEN_IDLE_DAYS == 90
    assert not hasattr(retention, "ACCOUNT_INACTIVITY_DELETION_DAYS")


# ── Guest clock ───────────────────────────────────────────────────────────────


def test_guest_retention_is_configurable_and_event_anchored():
    assert retention.GUEST_PII_AFTER_EVENT_DAYS == 548
    assert retention.GUEST_PII_AFTER_EVENT.days == 548


def test_guest_retention_carries_no_statutory_claim():
    """The docstring must describe it as a product decision."""
    source = (APP_ROOT / "core" / "retention.py").read_text(encoding="utf-8")
    block = source.split("GUEST_PII_AFTER_EVENT_DAYS")[0]
    assert "product retention decision" in block
    assert "no statutory claim" in block


def test_guest_expiry_query_uses_the_event_date_not_account_age():
    """Guard the anchoring, which is the whole point of the independent clock."""
    source = (
        APP_ROOT / "services" / "deletion" / "handlers" / "guests.py"
    ).read_text(encoding="utf-8")
    assert "Celebration.celebration_date < cutoff" in source
    assert "Invitation.event_date < cutoff" in source
    assert "last_login" not in source


# ── Review strategy ───────────────────────────────────────────────────────────


def test_review_strategy_default_is_the_reversible_one():
    """Defaults must not make an irreversible choice on the client's behalf."""
    assert retention.REVIEW_AUTHOR_STRATEGY == "tombstone"
    assert retention.SCRUB_REVIEW_FREE_TEXT is True


def test_invoice_pdf_purge_is_off_until_decided():
    assert retention.PURGE_INVOICE_PDFS is False


# ── Terminology ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "module",
    [
        "services/deletion/handlers/relationships.py",
        "services/deletion/handlers/identity.py",
    ],
)
def test_pseudonymisation_is_not_called_anonymisation(module: str):
    """Retained-but-linkable data must be described accurately.

    A surrogate that still resolves to a person is pseudonymous. Calling it
    anonymous in the code leads directly to calling it anonymous in the
    privacy policy, which would be untrue.
    """
    text = (APP_ROOT / module).read_text(encoding="utf-8").lower()
    if "pseudonymis" in text or "tombstone" in text:
        # Allowed only when explicitly contrasted with the weaker claim.
        if "anonymis" in text:
            assert "not anonymis" in text or "unlike" in text, (
                f"{module} uses 'anonymised' without distinguishing it from "
                "pseudonymisation"
            )
