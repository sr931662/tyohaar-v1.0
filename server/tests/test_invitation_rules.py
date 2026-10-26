"""
Invitation business rules and credentials — pure logic, no database.

The integration suite (test_invitations_integration.py) proves the rules are
wired through every endpoint; this file pins the rules themselves, including
the edges that are easy to get wrong: overnight events, time zones, the
check-out-after-revoke allowance, and code normalisation from scanners.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.core.rate_limit import InMemoryRateLimiter, RateLimitConfig
from app.models.enums import (
    CelebrationStatus as CS,
    GuestEntryAction as A,
    GuestEntryStatus as E,
    GuestPassStatus as P,
    GuestVerificationResult as R,
    RSVPStatus,
)
from app.services.invitations import credentials as cred
from app.services.invitations import rules
from app.services.invitations.rules import InvitationPolicy

TZ = "Asia/Kolkata"
POLICY = InvitationPolicy(entry_grace_minutes_before=60, entry_grace_minutes_after=60)
D = date(2026, 11, 14)


def _utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# ── Entry window ──────────────────────────────────────────────────────────────

def test_window_uses_event_timezone_and_grace():
    start, end = rules.entry_window(D, time(19, 0), time(23, 0), tz_name=TZ, policy=POLICY)
    # 19:00 IST = 13:30 UTC, minus 1h grace; 23:00 IST = 17:30 UTC, plus 1h.
    assert start == _utc(2026, 11, 14, 12, 30)
    assert end == _utc(2026, 11, 14, 18, 30)


def test_window_without_times_covers_the_whole_local_day():
    start, end = rules.entry_window(D, None, None, tz_name=TZ, policy=InvitationPolicy(
        entry_grace_minutes_before=0, entry_grace_minutes_after=0))
    assert start == _utc(2026, 11, 13, 18, 30)  # 00:00 IST
    assert end == _utc(2026, 11, 14, 18, 30)    # next 00:00 IST


def test_overnight_event_ends_the_next_day():
    start, end = rules.entry_window(D, time(21, 0), time(2, 0), tz_name=TZ, policy=POLICY)
    assert end - start == timedelta(hours=5 + 2)


# ── Evaluation ────────────────────────────────────────────────────────────────

WINDOW = (_utc(2026, 11, 14, 12), _utc(2026, 11, 14, 20))
INSIDE = _utc(2026, 11, 14, 15)


def _eval(action=A.CHECK_IN, *, pass_status=P.ACTIVE, entry=E.NOT_ARRIVED, rsvp=RSVPStatus.ATTENDING,
          plus=1, status=CS.CONFIRMED, now=INSIDE, policy=POLICY, party=None):
    return rules.evaluate(action=action, pass_status=pass_status, entry_status=entry, rsvp_status=rsvp,
                          plus_ones_allowed=plus, celebration_status=status, window=WINDOW, now=now,
                          policy=policy, party_size=party)


@pytest.mark.parametrize("kwargs,expected", [
    ({}, R.CHECKED_IN),
    ({"action": A.VERIFY}, R.VALID),
    ({"pass_status": P.REVOKED}, R.REVOKED),
    ({"status": CS.CANCELLED}, R.EVENT_CANCELLED),
    ({"status": CS.POSTPONED}, R.DENIED),
    ({"now": WINDOW[0] - timedelta(seconds=1)}, R.NOT_YET_VALID),
    ({"now": WINDOW[1] + timedelta(seconds=1)}, R.EXPIRED),
    ({"entry": E.CHECKED_IN}, R.ALREADY_CHECKED_IN),
    ({"entry": E.CHECKED_OUT}, R.ALREADY_USED),
    ({"party": 3, "plus": 1}, R.PARTY_SIZE_EXCEEDED),
    ({"party": 0}, R.PARTY_SIZE_EXCEEDED),
    ({"party": 2, "plus": 1}, R.CHECKED_IN),
])
def test_check_in_outcomes(kwargs, expected):
    assert _eval(**kwargs).result is expected


def test_revocation_outranks_every_other_state():
    assert _eval(pass_status=P.REVOKED, entry=E.CHECKED_IN, status=CS.CANCELLED).result is R.REVOKED


def test_reentry_only_when_policy_allows_and_is_flagged():
    allow = POLICY.model_copy(update={"allow_reentry": True})
    result = _eval(entry=E.CHECKED_OUT, policy=allow)
    assert result.result is R.CHECKED_IN and "reentry" in result.warnings


def test_declined_rsvp_warns_but_admits():
    result = _eval(rsvp=RSVPStatus.DECLINED)
    assert result.result is R.CHECKED_IN and result.warnings == ("rsvp_declined",)


def test_check_out_is_allowed_after_revocation_and_window_end():
    late = WINDOW[1] + timedelta(hours=3)
    assert _eval(A.CHECK_OUT, pass_status=P.REVOKED, entry=E.CHECKED_IN, now=late).result is R.CHECKED_OUT
    assert _eval(A.CHECK_OUT, entry=E.NOT_ARRIVED).result is R.NOT_CHECKED_IN


@pytest.mark.parametrize("kwargs,expected", [
    ({}, "valid"),
    ({"now": WINDOW[0] - timedelta(hours=1)}, "not_yet_valid"),
    ({"now": WINDOW[1] + timedelta(hours=1)}, "expired"),
    ({"entry": E.CHECKED_IN}, "checked_in"),
    ({"entry": E.CHECKED_OUT}, "used"),
    ({"pass_status": P.REVOKED}, "revoked"),
    ({"status": CS.CANCELLED}, "event_cancelled"),
    ({"status": CS.POSTPONED}, "postponed"),
])
def test_pass_state(kwargs, expected):
    args = {"pass_status": P.ACTIVE, "entry_status": E.NOT_ARRIVED, "celebration_status": CS.CONFIRMED,
            "window": WINDOW, "now": INSIDE, "policy": POLICY}
    rename = {"entry": "entry_status", "status": "celebration_status"}
    args.update({rename.get(k, k): v for k, v in kwargs.items()})
    assert rules.pass_state(**args) == expected


def test_rsvp_closes_the_day_of_the_event_and_on_revocation():
    assert rules.can_rsvp(pass_status=P.ACTIVE, celebration_status=CS.CONFIRMED, celebration_date=D, today=D - timedelta(days=1))
    assert not rules.can_rsvp(pass_status=P.ACTIVE, celebration_status=CS.CONFIRMED, celebration_date=D, today=D)
    assert not rules.can_rsvp(pass_status=P.REVOKED, celebration_status=CS.CONFIRMED, celebration_date=D, today=D - timedelta(days=5))
    assert not rules.can_rsvp(pass_status=P.ACTIVE, celebration_status=CS.CANCELLED, celebration_date=D, today=D - timedelta(days=5))


def test_invite_rules():
    ok = dict(celebration_status=CS.PLANNING, celebration_date=D, today=D - timedelta(days=3), policy=POLICY)
    assert rules.can_invite_to(**ok) is None
    assert rules.can_invite_to(**{**ok, "today": D + timedelta(days=1)})
    assert rules.can_invite_to(**{**ok, "celebration_status": CS.CANCELLED})
    assert rules.can_invite_to(**{**ok, "today": D - timedelta(days=POLICY.max_invite_days_in_advance + 1)})


@pytest.mark.parametrize("raw,expected", [
    ("+91 98765-43210", "+919876543210"),
    ("(987) 654 3210", "9876543210"),
    ("12", None),
    ("", None),
    ("98+7654321", "987654321"),
])
def test_normalize_phone(raw, expected):
    assert rules.normalize_phone(raw) == expected


def test_policy_bounds_are_enforced():
    with pytest.raises(ValueError):
        InvitationPolicy(max_plus_ones=-1)
    with pytest.raises(ValueError):
        InvitationPolicy(bulk_create_limit=10_000)


# ── Credentials ───────────────────────────────────────────────────────────────

def test_entry_code_normalisation_accepts_scanner_and_typed_forms():
    code = cred.new_entry_code()
    assert len(code) == 8 and set(code) <= set(cred.ENTRY_CODE_ALPHABET)
    for form in (code, code.lower(), cred.format_entry_code(code), f" {cred.qr_payload(code)} ", code[:4] + " " + code[4:]):
        assert cred.normalize_entry_code(form) == code
    for bad in ("", None, "ABC", "ABCDEFGHI", "ABCD-EFG0", "ILO01AAA"):
        assert cred.normalize_entry_code(bad) is None


def test_qr_payload_has_no_personal_data_or_ids():
    code = cred.new_entry_code()
    payload = cred.qr_payload(code)
    assert payload == f"TYH1:{code}" and len(payload) == 13


def test_hashes_are_keyed_and_kind_separated():
    assert cred.hash_secret("code", "ABCDEFGH") != cred.hash_secret("link", "ABCDEFGH")
    import hashlib
    assert cred.hash_secret("code", "ABCDEFGH") != hashlib.sha256(b"code:ABCDEFGH").hexdigest()


def test_encryption_round_trip_and_tamper_rejection():
    token = cred.new_link_token()
    assert len(token) >= 43
    enc = cred.encrypt(token)
    assert token not in enc and cred.decrypt(enc) == token
    assert cred.decrypt(enc[:-4] + "AAAA") is None
    assert cred.decrypt(None) is None


def test_issued_credentials_are_unique():
    issued = [cred.issue_guest_credentials() for _ in range(200)]
    assert len({c["link_token_hash"] for c in issued}) == 200
    assert len({c["entry_code_hash"] for c in issued}) == 200


def test_oversized_link_tokens_are_rejected_before_hashing():
    assert cred.link_lookup("x" * 129) is None
    assert cred.link_lookup("") is None


# ── Rate limiter ──────────────────────────────────────────────────────────────

async def test_in_memory_limiter_blocks_after_limit_and_reports_retry():
    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(requests=3, window_seconds=60, key_prefix="t")
    assert [await limiter.hit("k", config) for _ in range(4)] == [True, True, True, False]
    assert await limiter.hit("other", config)
    assert 1 <= await limiter.reset_after("k", config) <= 60
    assert await limiter.remaining("k", config) == 0
