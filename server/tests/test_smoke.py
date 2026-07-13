"""
Minimal smoke tests — no database required.

These only cover endpoints/paths that don't need a live Postgres connection,
so they can run in CI without provisioning a test database. Fuller
integration coverage (DB-backed) is tracked separately.
"""

import pytest


@pytest.mark.asyncio
async def test_liveness_probe(client):
    response = await client.get("/live")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_root_service_identity(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client):
    response = await client.get("/api/v1/bookings")
    assert response.status_code == 401
