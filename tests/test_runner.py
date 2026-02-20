"""Tests for the runner service POST /execute endpoint."""

import os

import pytest
import httpx
from runner.app import app


@pytest.fixture(autouse=True)
def set_allowed_root(monkeypatch):
    """Set ALLOWED_ROOT to /tmp so tests that use project_path=/tmp are allowed."""
    monkeypatch.setitem(os.environ, "ALLOWED_ROOT", "/tmp")


@pytest.mark.asyncio
async def test_post_execute_returns_json_with_contract_fields():
    """POST /execute with project_path and command returns JSON with exit_code, stdout, stderr, duration_seconds."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/execute",
            json={"project_path": "/tmp", "command": ["python3", "-c", "pass"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert "exit_code" in data
    assert "stdout" in data
    assert "stderr" in data
    assert "duration_seconds" in data
    assert isinstance(data["exit_code"], int)
    assert isinstance(data["stdout"], str)
    assert isinstance(data["stderr"], str)
    assert isinstance(data["duration_seconds"], (int, float))
    assert data["exit_code"] == 0


@pytest.mark.asyncio
async def test_post_execute_rejects_project_path_outside_allowed_root():
    """POST /execute with project_path outside ALLOWED_ROOT returns 400."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/execute",
            json={"project_path": "/etc", "command": ["python3", "-c", "pass"]},
        )
    assert response.status_code == 400
    data = response.json()
    assert data.get("code") == "invalid_input"
    assert "error" in data


@pytest.mark.asyncio
async def test_post_execute_rejects_command_not_in_allowlist():
    """POST /execute with command not in allowlist (e.g. rm -rf) returns 400."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/execute",
            json={"project_path": "/tmp", "command": ["rm", "-rf", "/"]},
        )
    assert response.status_code == 400
    data = response.json()
    assert data.get("code") == "invalid_input"
    assert "error" in data
