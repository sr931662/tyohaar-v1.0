"""
Authentication hardening. Each test pins one finding from the auth review.
No database: units of work and repositories are stubbed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.core import current_user as cu
from app.core import rate_limit
from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import AccountStatus, LoginMethod, OTPDeliveryChannel, OTPPurpose, OTPStatus
from app.services.auth import validators
from app.services.auth.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    OTPAttemptsExhaustedError,
    OTPInvalidError,
)
from app.services.auth.helpers import encode_jwt, hash_otp
from app.services.auth.service import AuthService, TokenPairResponse
from app.services.exceptions import BusinessRuleError, ExternalServiceError, RateLimitError
from app.services.notifications import sms_client


# ── 1. Wrong OTP attempts must survive the rollback ──────────────────────────

class _OtpUow:
    def __init__(self, record):
        self.auth = SimpleNamespace(otps=SimpleNamespace(find_pending=self._find))
        self.record = record
        self.commits = 0
        self.session = SimpleNamespace(flush=self._noop)

    async def _find(self, identifier, purpose):
        return self.record

    async def _noop(self):
        return None

    async def commit(self):
        self.commits += 1


def _otp(code="123456", identifier="+919876543210"):
    return SimpleNamespace(
        otp_hash=hash_otp(identifier, code, settings.SECRET_KEY),
        attempt_count=0, max_attempts=3, status=OTPStatus.PENDING,
        is_expired=False, is_attempts_exhausted=False, verified_at=None,
    )


@pytest.mark.asyncio
async def test_a_wrong_code_is_committed_before_the_error():
    rec = _otp()
    uow = _OtpUow(rec)
    with pytest.raises(OTPInvalidError):
        await validators.validate_otp_for_verification("+919876543210", "000000", OTPPurpose.LOGIN, uow, settings.SECRET_KEY)
    assert rec.attempt_count == 1
    assert uow.commits == 1  # flush alone was rolled back by the unit of work


@pytest.mark.asyncio
async def test_the_third_wrong_code_exhausts_the_otp():
    rec = _otp()
    uow = _OtpUow(rec)
    for _ in range(2):
        with pytest.raises(OTPInvalidError):
            await validators.validate_otp_for_verification("+919876543210", "000000", OTPPurpose.LOGIN, uow, settings.SECRET_KEY)
    with pytest.raises(OTPAttemptsExhaustedError):
        await validators.validate_otp_for_verification("+919876543210", "000000", OTPPurpose.LOGIN, uow, settings.SECRET_KEY)
    assert rec.status == OTPStatus.EXHAUSTED and uow.commits == 3


# ── 2. Password lockout ──────────────────────────────────────────────────────

class _CommitUow:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class _LockableUser(SimpleNamespace):
    @property
    def is_locked(self) -> bool:
        return self.account_locked_until is not None and datetime.now(timezone.utc) < self.account_locked_until


def _user(**kw):
    base = dict(failed_login_count=0, account_locked_until=None)
    base.update(kw)
    return _LockableUser(**base)


@pytest.mark.asyncio
async def test_five_wrong_passwords_lock_the_account():
    user, uow = _user(), _CommitUow()
    for _ in range(4):
        with pytest.raises(InvalidCredentialsError):
            await AuthService._check_password(uow, user, False)
    assert user.account_locked_until is None and user.failed_login_count == 4
    with pytest.raises(InvalidCredentialsError):
        await AuthService._check_password(uow, user, False)
    assert user.account_locked_until is not None and uow.commits == 5


@pytest.mark.asyncio
async def test_a_locked_account_is_refused_even_with_the_right_password():
    user = _user(account_locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))
    with pytest.raises(AccountLockedError, match="one-time code"):
        await AuthService._check_password(_CommitUow(), user, True)


@pytest.mark.asyncio
async def test_a_right_password_clears_the_counter():
    user = _user(failed_login_count=3)
    await AuthService._check_password(_CommitUow(), user, True)
    assert user.failed_login_count == 0


# ── 3. One-time-code sign-in is also sign-up, by email or phone ─────────────

class _Users:
    def __init__(self, by_email=None, by_phone=None):
        self.by_email, self.by_phone, self.created = by_email, by_phone, []

    async def find_by_email(self, e):
        return self.by_email

    async def find_by_phone(self, p):
        return self.by_phone

    async def create_from_dict(self, d):
        self.created.append(d)
        return SimpleNamespace(id=uuid.uuid4(), **d)


class _VerifyUow:
    def __init__(self, users):
        self.users = SimpleNamespace(users=users, profiles=SimpleNamespace(create_from_dict=self._profile))
        self.session = SimpleNamespace(flush=self._noop)

    async def _profile(self, d):
        return d

    async def _noop(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *e):
        return False


@pytest.fixture
def otp_service(monkeypatch):
    sessions = []

    async def ok(*a, **k):
        return None

    async def session(self_, user, ip, ua, method, device_id=None):
        sessions.append((user, method))
        return TokenPairResponse(access_token="a", refresh_token="r", user_id=user.id)

    monkeypatch.setattr("app.services.auth.service.validate_otp_for_verification", ok)
    monkeypatch.setattr(AuthService, "_create_user_session", session)

    def make(users):
        svc = AuthService()
        monkeypatch.setattr(svc, "_uow", lambda: _VerifyUow(users), raising=False)
        return svc

    make.sessions = sessions
    return make


def _verify(identifier, purpose=OTPPurpose.LOGIN):
    return SimpleNamespace(identifier=identifier, otp_code="123456", purpose=purpose)


@pytest.mark.asyncio
async def test_new_email_signs_up_verified(otp_service):
    users = _Users()
    tokens = await otp_service(users).verify_otp(_verify("asha@example.com"))
    created = users.created[0]
    assert created["email"] == "asha@example.com" and created["email_verified"] is True
    assert created["phone"].startswith("TMP-")
    assert tokens.is_new_user is True
    assert otp_service.sessions[0][1] is LoginMethod.OTP_EMAIL


@pytest.mark.asyncio
async def test_new_phone_signs_up_verified(otp_service):
    users = _Users()
    tokens = await otp_service(users).verify_otp(_verify("+919876543210"))
    created = users.created[0]
    assert created["phone"] == "+919876543210" and created["phone_verified"] is True
    assert tokens.is_new_user is True


@pytest.mark.asyncio
async def test_existing_account_signs_in_and_gets_verified(otp_service):
    existing = SimpleNamespace(id=uuid.uuid4(), account_status=AccountStatus.ACTIVE, email_verified=False,
                               phone_verified=False, failed_login_count=4,
                               account_locked_until=datetime.now(timezone.utc) + timedelta(minutes=5))
    tokens = await otp_service(_Users(by_email=existing)).verify_otp(_verify("asha@example.com"))
    assert tokens.is_new_user is False
    assert existing.email_verified is True
    assert existing.account_locked_until is None  # a code unlocks a password lockout


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [AccountStatus.SUSPENDED, AccountStatus.BANNED, AccountStatus.DEACTIVATED])
async def test_a_code_never_reopens_a_blocked_account(otp_service, status):
    blocked = SimpleNamespace(id=uuid.uuid4(), account_status=status, email_verified=False, phone_verified=False)
    with pytest.raises(AccountLockedError):
        await otp_service(_Users(by_phone=blocked)).verify_otp(_verify("+919876543210"))
    assert blocked.account_status is status


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", [OTPPurpose.PASSWORD_RESET, OTPPurpose.EMAIL_VERIFICATION, OTPPurpose.ACCOUNT_DELETION])
async def test_codes_for_other_purposes_cannot_sign_in(otp_service, purpose):
    users = _Users()
    with pytest.raises(OTPInvalidError):
        await otp_service(users).verify_otp(_verify("asha@example.com", purpose))
    assert users.created == []


# ── 4. Rate limiting and the real client IP ──────────────────────────────────

def _request(xff="", path="/api/v1/auth/login", host="10.0.0.1"):
    return SimpleNamespace(headers={"X-Forwarded-For": xff} if xff else {},
                           client=SimpleNamespace(host=host), url=SimpleNamespace(path=path))


def test_the_spoofable_first_forwarded_entry_is_ignored():
    assert rate_limit.client_ip(_request("6.6.6.6, 203.0.113.9")) == "203.0.113.9"
    assert rate_limit.client_ip(_request("203.0.113.9")) == "203.0.113.9"
    assert rate_limit.client_ip(_request()) == "10.0.0.1"


@pytest.mark.asyncio
async def test_auth_endpoints_are_rate_limited_per_ip(monkeypatch):
    monkeypatch.setattr(rate_limit, "_auth_limiter", rate_limit.InMemoryRateLimiter())
    limit = rate_limit.AUTH_ENDPOINT_RATE_LIMIT.requests
    for _ in range(limit):
        await rate_limit.auth_rate_limit(_request("203.0.113.9"))
    with pytest.raises(RateLimitError):
        await rate_limit.auth_rate_limit(_request("203.0.113.9"))
    # rotating a fake first entry doesn't help
    with pytest.raises(RateLimitError):
        await rate_limit.auth_rate_limit(_request("1.2.3.4, 203.0.113.9"))
    # another IP, or another endpoint, has its own budget
    await rate_limit.auth_rate_limit(_request("198.51.100.7"))
    await rate_limit.auth_rate_limit(_request("203.0.113.9", path="/api/v1/auth/otp/verify"))


# ── 5. A logged-out token stops working ──────────────────────────────────────

def _session_token(sid):
    return encode_jwt({"sub": str(uuid.uuid4()), "session_id": str(sid),
                       "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
                      settings.SECRET_KEY, settings.ALGORITHM)


@pytest.mark.asyncio
async def test_a_revoked_session_is_refused(monkeypatch):
    async def inactive(self, sid):
        return False

    monkeypatch.setattr(AuthService, "session_is_active", inactive)
    cu._active_sessions.clear()
    with pytest.raises(HTTPException) as e:
        await cu._assert_session_active(_session_token(uuid.uuid4()))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_an_active_session_is_cached(monkeypatch):
    calls = []

    async def active(self, sid):
        calls.append(sid)
        return True

    monkeypatch.setattr(AuthService, "session_is_active", active)
    cu._active_sessions.clear()
    token = _session_token(uuid.uuid4())
    await cu._assert_session_active(token)
    await cu._assert_session_active(token)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_logout_evicts_the_cache_immediately(monkeypatch):
    state = {"active": True}

    async def check(self, sid):
        return state["active"]

    monkeypatch.setattr(AuthService, "session_is_active", check)
    cu._active_sessions.clear()
    sid = uuid.uuid4()
    await cu._assert_session_active(_session_token(sid))
    state["active"] = False
    cu.forget_session(str(sid))
    with pytest.raises(HTTPException):
        await cu._assert_session_active(_session_token(sid))


@pytest.mark.asyncio
async def test_tokens_without_a_session_claim_are_unaffected():
    await cu._assert_session_active(create_access_token(str(uuid.uuid4())))


# ── 6. Code channel must match the identifier ────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("identifier,channel", [("asha@example.com", OTPDeliveryChannel.SMS), ("+919876543210", OTPDeliveryChannel.EMAIL)])
async def test_mismatched_channel_is_rejected(identifier, channel):
    from app.controllers.auth.controller import request_otp
    from app.services.exceptions import ValidationError

    body = SimpleNamespace(identifier=identifier, channel=channel, purpose=OTPPurpose.LOGIN, device_fingerprint=None)
    request = SimpleNamespace(headers={}, client=None)
    with pytest.raises(ValidationError):
        await request_otp(body, service=None, request=request)


# ── 7. SMS providers ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_msg91_request_shape(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["headers"], seen["body"] = str(request.url), request.headers, request.content
        return httpx.Response(200, json={"type": "success"})

    for k, v in dict(SMS_PROVIDER="msg91", SMS_API_KEY="key123", SMS_TEMPLATE_ID="tmpl9", SMS_TEMPLATE_OTP_VAR="otp").items():
        monkeypatch.setattr(settings, k, v, raising=False)
    await sms_client.send_otp_sms("+91 98765-43210", "482913", transport=httpx.MockTransport(handler))
    import json
    body = json.loads(seen["body"])
    assert seen["url"] == "https://control.msg91.com/api/v5/flow"
    assert seen["headers"]["authkey"] == "key123"
    assert body["template_id"] == "tmpl9"
    assert body["recipients"] == [{"mobiles": "919876543210", "otp": "482913"}]


@pytest.mark.asyncio
async def test_twilio_request_shape(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"], seen["auth"] = str(request.url), request.content.decode(), request.headers["authorization"]
        return httpx.Response(201, json={"sid": "SM1"})

    for k, v in dict(SMS_PROVIDER="twilio", SMS_ACCOUNT_SID="AC1", SMS_API_KEY="tok", SMS_SENDER="+15550001111").items():
        monkeypatch.setattr(settings, k, v, raising=False)
    await sms_client.send_otp_sms("+919876543210", "482913", transport=httpx.MockTransport(handler))
    assert seen["url"].endswith("/Accounts/AC1/Messages.json")
    assert "To=%2B919876543210" in seen["body"] and "482913" in seen["body"]
    assert seen["auth"].startswith("Basic ")


@pytest.mark.asyncio
async def test_provider_rejection_raises_without_leaking_the_code(monkeypatch, caplog):
    for k, v in dict(SMS_PROVIDER="msg91", SMS_API_KEY="k", SMS_TEMPLATE_ID="t").items():
        monkeypatch.setattr(settings, k, v, raising=False)
    transport = httpx.MockTransport(lambda r: httpx.Response(401, text="bad key, otp=482913"))
    with pytest.raises(RuntimeError):
        await sms_client.send_otp_sms("+919876543210", "482913", transport=transport)
    assert "482913" not in caplog.text


def test_sms_not_configured_by_default(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "", raising=False)
    assert sms_client.is_configured() is False


# ── 8. Provider config tells the app what sign-in options exist ─────────────

def test_production_without_providers_reports_otp_unavailable(monkeypatch):
    from app.services.notifications import email_client

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))
    monkeypatch.setattr(sms_client, "is_configured", lambda: False)
    monkeypatch.setattr(email_client, "is_configured", lambda: True)
    cfg = AuthService().get_provider_config()
    assert cfg.email_otp_enabled is True and cfg.phone_otp_enabled is False


def test_development_always_offers_both(monkeypatch):
    from app.services.notifications import email_client

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: False))
    monkeypatch.setattr(sms_client, "is_configured", lambda: False)
    monkeypatch.setattr(email_client, "is_configured", lambda: False)
    cfg = AuthService().get_provider_config()
    assert cfg.email_otp_enabled and cfg.phone_otp_enabled


# ── 9. Production phone codes: real SMS or a clear refusal, never the log ────

class _SendUow:
    def __init__(self):
        self.auth = SimpleNamespace(otps=SimpleNamespace(supersede_all_pending=self._noop, create=self._create))

    async def _noop(self, *a, **k):
        return None

    async def _create(self, record):
        # Column defaults the database would fill in.
        record.resend_count, record.max_resends, record.attempt_count = 0, 3, 0
        return record

    async def __aenter__(self):
        return self

    async def __aexit__(self, *e):
        return False


@pytest.fixture
def sender(monkeypatch):
    async def ok(*a, **k):
        return None

    monkeypatch.setattr("app.services.auth.service.validate_otp_rate_limit", ok)
    svc = AuthService()
    monkeypatch.setattr(svc, "_uow", lambda: _SendUow(), raising=False)
    monkeypatch.setattr(svc, "_push_otp", ok, raising=False)
    return svc


@pytest.mark.asyncio
async def test_production_without_sms_refuses_phone_codes(sender, monkeypatch, caplog):
    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))
    monkeypatch.setattr(sms_client, "is_configured", lambda: False)
    with pytest.raises(ExternalServiceError, match="isn't available"):
        await sender.send_otp("+919876543210", OTPDeliveryChannel.SMS, OTPPurpose.LOGIN)
    assert "[SMS STUB] OTP for" not in caplog.text


@pytest.mark.asyncio
async def test_configured_sms_sends_the_code(sender, monkeypatch):
    sent = []

    async def fake_send(phone, code, **k):
        sent.append((phone, code))

    monkeypatch.setattr(sms_client, "is_configured", lambda: True)
    monkeypatch.setattr(sms_client, "send_otp_sms", fake_send)
    await sender.send_otp("+919876543210", OTPDeliveryChannel.SMS, OTPPurpose.LOGIN)
    assert sent[0][0] == "+919876543210" and len(sent[0][1]) == 6


# ── 10. Booking needs a verified contact ─────────────────────────────────────

@pytest.mark.asyncio
async def test_unverified_customers_cannot_book(monkeypatch):
    from app.services.bookings.service import BookingService

    unverified = SimpleNamespace(email_verified=False, phone_verified=False)

    class Uow:
        users = SimpleNamespace(users=SimpleNamespace(get_by_id=lambda _id: _ret(unverified)))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

    async def _ret(v):
        return v

    svc = BookingService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(), raising=False)
    monkeypatch.setattr("app.services.bookings.service.validate_booking_cutoff", lambda dt: None)
    data = SimpleNamespace(scheduled_date=date.today() + timedelta(days=30), scheduled_start_time=None)
    monkeypatch.setattr(svc, "_scheduled_event_dt", lambda d: None, raising=False)
    with pytest.raises(BusinessRuleError, match="verify your email address or phone"):
        await svc.create_booking(uuid.uuid4(), data)


# ── 11. Admin passwords move from a fast HMAC to bcrypt ──────────────────────

def test_new_admin_hashes_are_bcrypt_and_verify():
    from app.services.admin.helpers import admin_hash_needs_upgrade, hash_admin_password, verify_admin_password

    h = hash_admin_password("S3cure-pass!")
    assert h.startswith("$2") and not admin_hash_needs_upgrade(h)
    assert verify_admin_password("S3cure-pass!", h)
    assert not verify_admin_password("wrong", h)


def test_legacy_hmac_hashes_still_work_and_are_flagged_for_upgrade():
    import hashlib
    import hmac as _hmac

    from app.services.admin.helpers import admin_hash_needs_upgrade, verify_admin_password

    legacy = _hmac.new(settings.SECRET_KEY.encode(), b"Old-pass1", hashlib.sha256).hexdigest()
    assert verify_admin_password("Old-pass1", legacy)
    assert not verify_admin_password("nope", legacy)
    assert admin_hash_needs_upgrade(legacy)
    assert not verify_admin_password("anything", "")
