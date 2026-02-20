"""Tests for the crew API POST /run endpoint (Runner integration)."""

import pytest
import httpx
from crew_api.app import app


def _make_mock_runner_transport(exit_code: int = 0, stdout: str = "", stderr: str = "", duration_seconds: float = 1.0):
    """Build a MockTransport that responds to POST /execute with the given Runner payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/execute" and request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "duration_seconds": duration_seconds,
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_post_run_run_tests_returns_200_with_success_exit_code_summary():
    """POST /run with project_path and action run_tests returns 200 and body has success, exit_code, summary."""
    runner_url = "http://runner:8080"
    mock_transport = _make_mock_runner_transport(
        exit_code=0,
        stdout="3 passed in 0.12s",
        stderr="",
        duration_seconds=0.5,
    )
    app.state.runner_url = runner_url
    app.state.runner_transport = mock_transport

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/run",
            json={"project_path": "/tmp/proj", "action": "run_tests"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    assert "exit_code" in data
    assert data["exit_code"] == 0
    assert "summary" in data
    assert "stdout" in data
    assert data["stdout"] == "3 passed in 0.12s"
    assert "stderr" in data
    assert "duration_seconds" in data
    assert data["duration_seconds"] == 0.5
