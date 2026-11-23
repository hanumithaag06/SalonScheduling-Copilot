# Why: Verifies the /health endpoint returns 200 and expected payload.
# This is the first test — proves pytest + httpx + FastAPI are wired up.

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health should return status=healthy and version=0.1.0."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
