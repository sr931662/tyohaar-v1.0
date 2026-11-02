from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models.enums import NotificationChannel, NotificationType
from app.services.notifications import email_client
from app.services.notifications.service import NotificationService


@pytest.mark.asyncio
async def test_notify_pushes_by_default(monkeypatch):
    seen = []
    svc = NotificationService()

    async def send(user_id, data):
        seen.append((user_id, data))

    monkeypatch.setattr(svc, "send_notification", send)
    uid, ref = uuid.uuid4(), uuid.uuid4()
    await svc.notify(uid, NotificationType.REFUND_INITIATED, "Refund initiated", "body", reference_type="refund", reference_id=ref)
    assert seen[0][0] == uid
    d = seen[0][1]
    assert d.channel is NotificationChannel.PUSH and d.title == "Refund initiated"
    assert d.reference_type == "refund" and d.reference_id == ref


@pytest.mark.asyncio
async def test_notify_never_raises(monkeypatch):
    svc = NotificationService()

    async def boom(user_id, data):
        raise RuntimeError("db down")

    monkeypatch.setattr(svc, "send_notification", boom)
    await svc.notify(uuid.uuid4(), NotificationType.SYSTEM, "t", "b")  # must not raise


@pytest.mark.asyncio
async def test_generic_email_uses_the_branded_shell_and_escapes_the_body(monkeypatch):
    sent = {}

    async def fake_send(to, subject, html_body, text_body=None, attachments=None):
        sent.update(to=to, subject=subject, html=html_body)

    monkeypatch.setattr(email_client, "is_configured", lambda: True)
    monkeypatch.setattr(email_client, "send_email", fake_send)

    notif = SimpleNamespace(id=uuid.uuid4())

    class Repo:
        async def get_by_id(self, _id):
            return SimpleNamespace(email="a@example.com") if _id != notif.id else notif

        async def update(self, obj, data):
            return obj

    class Uow:
        users = SimpleNamespace(users=Repo())
        notifications = SimpleNamespace(notifications=Repo())

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

    svc = NotificationService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(), raising=False)
    await svc._dispatch_email(notif.id, uuid.uuid4(), "Hello", "line one\n<script>x</script>")

    assert sent["to"] == "a@example.com"
    assert "Tyohaar" in sent["html"] and "<br>" in sent["html"]
    assert "<script>" not in sent["html"] and "&lt;script&gt;" in sent["html"]
