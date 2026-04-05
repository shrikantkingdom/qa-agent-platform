import pytest


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_providers(client):
    resp = await client.get("/api/v1/providers")
    assert resp.status_code == 200
    assert "providers" in resp.json()


@pytest.mark.anyio
async def test_config(client):
    resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
