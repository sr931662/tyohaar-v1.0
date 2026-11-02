"""
OTP delivery by push. The code goes only to devices already signed in to the
account it belongs to, never to whoever happened to request it.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models.enums import OTPPurpose
from app.services.auth.service import AuthService
from app.services.notifications import fcm_client


class _Users:
    def __init__(self, user):
        self.user = user
        self.looked_up = None

    async def find_by_phone_or_email(self, identifier):
        self.looked_up = identifier
        return self.user


class _Devices:
    def __init__(self, devices):
        self.devices = devices
        self.deactivated = []

    async def find_by_user(self, _uid):
        return self.devices

    async def find_by_token(self, token):
        return next((d for d in self.devices if d.push_notification_token == token), None)

    async def update(self, device, data):
        self.deactivated.append((device, data))


def _service(monkeypatch, user, devices):
    users, devs = _Users(user), _Devices(devices)
    uow = SimpleNamespace(users=SimpleNamespace(users=users, devices=devs))

    class Ctx:
        async def __aenter__(self_):
            return uow

        async def __aexit__(self_, *exc):
            return False

    svc = AuthService()
    monkeypatch.setattr(svc, "_uow", lambda: Ctx(), raising=False)
    return svc, users, devs


def _device(token, active=True):
    return SimpleNamespace(push_notification_token=token, is_active=active)


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def fake_send(tokens, title, body, data=None):
        calls.append(SimpleNamespace(tokens=tokens, title=title, body=body, data=data))
        return fcm_client.PushResult(len(tokens), 0, ["dead"] if "dead" in tokens else [], {})

    monkeypatch.setattr(fcm_client, "is_configured", lambda: True)
    monkeypatch.setattr(fcm_client, "send_push", fake_send)
    return calls


@pytest.mark.asyncio
async def test_code_is_pushed_to_the_accounts_active_devices_only(monkeypatch, sent):
    svc, users, _ = _service(monkeypatch, SimpleNamespace(id=uuid.uuid4()), [_device("a"), _device("b", active=False), _device(None)])
    await svc._push_otp("anita@example.com", "482913", OTPPurpose.PASSWORD_RESET)

    assert users.looked_up == "anita@example.com"
    assert len(sent) == 1 and sent[0].tokens == ["a"]
    assert "482913" in sent[0].title and "reset your password" in sent[0].body
    assert sent[0].data == {"type": "otp"}


@pytest.mark.asyncio
async def test_unknown_account_gets_nothing_pushed(monkeypatch, sent):
    svc, _, _ = _service(monkeypatch, None, [_device("a")])
    await svc._push_otp("nobody@example.com", "111111", OTPPurpose.LOGIN)
    assert sent == []


@pytest.mark.asyncio
async def test_no_devices_means_no_push(monkeypatch, sent):
    svc, _, _ = _service(monkeypatch, SimpleNamespace(id=uuid.uuid4()), [])
    await svc._push_otp("+919876543210", "111111", OTPPurpose.LOGIN)
    assert sent == []


@pytest.mark.asyncio
async def test_firebase_not_configured_is_a_quiet_noop(monkeypatch):
    monkeypatch.setattr(fcm_client, "is_configured", lambda: False)
    svc, users, _ = _service(monkeypatch, SimpleNamespace(id=uuid.uuid4()), [_device("a")])
    await svc._push_otp("+919876543210", "111111", OTPPurpose.LOGIN)
    assert users.looked_up is None


@pytest.mark.asyncio
async def test_dead_tokens_are_deactivated(monkeypatch, sent):
    svc, _, devs = _service(monkeypatch, SimpleNamespace(id=uuid.uuid4()), [_device("dead"), _device("ok")])
    await svc._push_otp("+919876543210", "111111", OTPPurpose.LOGIN)
    assert [d["is_active"] for _, d in devs.deactivated] == [False]


@pytest.mark.asyncio
async def test_a_push_failure_never_breaks_the_request(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("fcm down")

    monkeypatch.setattr(fcm_client, "is_configured", lambda: True)
    monkeypatch.setattr(fcm_client, "send_push", boom)
    svc, _, _ = _service(monkeypatch, SimpleNamespace(id=uuid.uuid4()), [_device("a")])
    await svc._push_otp("+919876543210", "111111", OTPPurpose.LOGIN)  # must not raise
