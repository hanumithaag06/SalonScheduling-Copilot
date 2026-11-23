# Why: Verifies the /health endpoint returns 200 and expected payload.

import pytest
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health should return status=healthy and matching app version."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == app.version
