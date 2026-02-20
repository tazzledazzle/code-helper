"""Tests for the crew API GET /health endpoint."""

import pytest
import httpx
from crew_api.app import app


@pytest.mark.asyncio
async def test_get_health_returns_200_and_ok():
    """GET /health returns 200 and {"status": "ok"}."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
