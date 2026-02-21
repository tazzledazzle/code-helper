"""Tests for the crew API GET /project and POST /project endpoints."""

import pytest
import httpx
from unittest.mock import patch

from crew_api.app import app
from crew_api.ingest_job import IngestJobAlreadyActive


@pytest.fixture(autouse=True)
def mock_ingest_job_create():
    """Mock ingest job creation so tests do not require a K8s cluster."""
    with patch("crew_api.app.ingest_job.create", return_value="ingest-fake-0"):
        yield


@pytest.mark.asyncio
async def test_post_project_returns_200_and_accepted_or_indexing():
    """POST /project with {"project_path": "/some/path"} returns 200 and status accepted or indexing."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/project", json={"project_path": "/some/path"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("accepted", "indexing")


@pytest.mark.asyncio
async def test_get_project_returns_project_path_and_index_status():
    """GET /project returns project_path and optional index_status."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/project")
    assert response.status_code == 200
    data = response.json()
    assert "project_path" in data
    assert "index_status" in data
    assert data["index_status"] in ("idle", "indexing", "ready", "failed")


@pytest.mark.asyncio
async def test_post_then_get_returns_set_path_and_index_status():
    """POST /project then GET /project returns the set path and index_status."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_response = await client.post("/project", json={"project_path": "/my/project"})
        assert post_response.status_code == 200
        get_response = await client.get("/project")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["project_path"] == "/my/project"
    assert data["index_status"] in ("idle", "indexing", "ready", "failed")


@pytest.mark.asyncio
async def test_post_project_with_pinned_repo():
    """POST /project with pinned_repo then GET returns pinned_repo."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/project",
            json={"project_path": "/other/path", "pinned_repo": "owner/repo"},
        )
        response = await client.get("/project")
    assert response.status_code == 200
    data = response.json()
    assert data["project_path"] == "/other/path"
    assert data.get("pinned_repo") == "owner/repo"


@pytest.mark.asyncio
async def test_post_project_returns_409_when_already_indexing():
    """POST /project returns 409 with error already_indexing and job_id when Job for same project is active."""
    with patch("crew_api.app.ingest_job.create", side_effect=IngestJobAlreadyActive("ingest-abc12345")):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.get("/health")  # ensure app.state.settings exists
            response = await client.post("/project", json={"project_path": "/same/path"})
    assert response.status_code == 409
    data = response.json()
    assert data.get("error") == "already_indexing"
    assert data.get("job_id") == "ingest-abc12345"
