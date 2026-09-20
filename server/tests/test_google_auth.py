"""
Google Sign-In endpoint contract. No database required: every case here is
rejected before the service reaches a repository.
"""

from __future__ import annotations

import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_auth_config_is_public_and_reports_google_state(client):
    response = await client.get("/api/v1/auth/config")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["google_client_id"] == settings.GOOGLE_CLIENT_ID
    # The flag is what the app checks before showing the Google button, so it
    # must track whether a client ID is actually set.
    assert data["google_enabled"] is bool(settings.GOOGLE_CLIENT_ID)


@pytest.mark.asyncio
async def test_google_sign_in_requires_an_id_token(client):
    response = await client.post("/api/v1/auth/google", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_google_sign_in_rejects_a_bogus_token(client):
    """
    Unconfigured (no GOOGLE_CLIENT_ID) and configured-but-invalid must both
    fail closed. What must never happen is a 2xx that mints a session.
    """
    response = await client.post(
        "/api/v1/auth/google", json={"id_token": "not-a-real-google-jwt"}
    )
    assert response.status_code >= 400
    assert "access_token" not in response.text
