"""
The host is told when invitations are created and first shared, once each.
Internals are stubbed (no database); only the notice decisions are asserted.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.invitations.service import InvitationService


class _Guests:
    async def exists_where(self, *a, **k):
        return False

    async def update(self, guest, data):
        for k, v in data.items():
            setattr(guest, k, v)
        return guest


class _Uow:
    occasions = SimpleNamespace(guests=_Guests())
    session = SimpleNamespace()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def harness(monkeypatch):
    celebration = SimpleNamespace(id=uuid.uuid4(), title="Anita's 25th")
    guest = SimpleNamespace(name="Ravi", invitation_sent_at=None, share_count=0, pass_status=None)
    notes: list[tuple] = []
    svc = InvitationService()
    monkeypatch.setattr(svc, "_uow", lambda: _Uow(), raising=False)

    async def owned(uow, cid, uid, lock=False):
        return celebration

    async def guest_in(uow, cid, gid, lock=False):
        return guest

    async def policy(uow):
        return SimpleNamespace()

    async def noop(*a, **k):
        return None

    async def notify(user_id, ntype, title, body, celebration_id):
        notes.append((user_id, title, body, celebration_id))

    monkeypatch.setattr(InvitationService, "_owned_celebration", staticmethod(owned))
    monkeypatch.setattr(InvitationService, "_guest_in", staticmethod(guest_in))
    monkeypatch.setattr(InvitationService, "load_policy", staticmethod(policy))
    monkeypatch.setattr(InvitationService, "_notify", staticmethod(notify))
    monkeypatch.setattr(svc, "_assert_can_invite", noop, raising=False)
    monkeypatch.setattr(svc, "_history", noop, raising=False)
    monkeypatch.setattr(svc, "_host_view", lambda *a, **k: "view", raising=False)
    return svc, celebration, guest, notes


def _user():
    return SimpleNamespace(id=uuid.uuid4(), first_name="Anita", last_name="Rao", full_name="Anita Rao", phone="+91")


@pytest.mark.asyncio
async def test_creating_an_invitation_tells_the_host(harness, monkeypatch):
    svc, celebration, guest, notes = harness

    async def create_one(uow, c, data, policy, actor, client_request_id=None):
        return guest, True

    monkeypatch.setattr(svc, "_create_one", create_one, raising=False)
    user = _user()
    await svc.create_invitation(celebration.id, user, SimpleNamespace(client_request_id="r1"), base_url=None)

    assert len(notes) == 1
    assert notes[0][0] == user.id and notes[0][1] == "Invitation created"
    assert "Ravi" in notes[0][2] and "Anita's 25th" in notes[0][2]


@pytest.mark.asyncio
async def test_a_replayed_create_does_not_notify_again(harness, monkeypatch):
    svc, celebration, guest, notes = harness

    async def create_one(uow, c, data, policy, actor, client_request_id=None):
        return guest, False  # idempotent replay: the guest already existed

    monkeypatch.setattr(svc, "_create_one", create_one, raising=False)
    await svc.create_invitation(celebration.id, _user(), SimpleNamespace(client_request_id="r1"), base_url=None)
    assert notes == []


@pytest.mark.asyncio
async def test_first_share_notifies_and_a_reshare_does_not(harness):
    svc, celebration, guest, notes = harness
    user = _user()
    await svc.mark_shared(celebration.id, uuid.uuid4(), user, "whatsapp", base_url=None)
    assert [n[1] for n in notes] == ["Invitation shared"]
    assert "Ravi" in notes[0][2]

    await svc.mark_shared(celebration.id, uuid.uuid4(), user, "whatsapp", base_url=None)
    assert len(notes) == 1  # still one: invitation_sent_at is now set


@pytest.mark.asyncio
async def test_no_entry_code_is_ever_put_in_a_notice(harness):
    svc, celebration, guest, notes = harness
    guest.entry_code_enc = "SECRET-CODE"
    await svc.mark_shared(celebration.id, uuid.uuid4(), _user(), "sms", base_url=None)
    assert "SECRET" not in " ".join(str(part) for note in notes for part in note)
