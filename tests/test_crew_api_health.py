"""Tests for the crew API GET /health and GET /readyz endpoints."""

import pytest
import httpx
from crew_api.app import app


@pytest.mark.asyncio
async def test_get_health_returns_200_and_ok():
    """GET /health returns 200 and {"status": "ok"} (liveness, process-only)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_readyz_returns_503_when_llm_not_configured():
    """GET /readyz returns 503 and per-check details when LLM URL is empty."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/readyz")
    # With no LLM_URL/OPENAI_BASE_URL, llm is "not_configured" -> not ready
    assert response.status_code == 503
    data = response.json()
    assert data["ready"] is False
    assert "runner" in data
    assert "chroma" in data
    assert data["llm"] == "not_configured"


@pytest.mark.asyncio
async def test_get_readyz_returns_json_with_required_keys():
    """GET /readyz returns JSON with ready, runner, chroma, llm."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/readyz")
    data = response.json()
    assert "ready" in data
    assert "runner" in data
    assert "chroma" in data
    assert "llm" in data
    assert isinstance(data["ready"], bool)
    assert isinstance(data["runner"], str)
    assert isinstance(data["chroma"], str)
    assert isinstance(data["llm"], str)
