"""Tests for POST /project creating a K8s Ingest Job."""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from crew_api.app import app
from crew_api.config import CrewApiSettings


@pytest.mark.asyncio
async def test_post_project_creates_k8s_job_with_project_path_and_ingest_image():
    """POST /project with project_path results in create_namespaced_job called with Job spec containing project_path and ingest image."""
    project_path = "/workspace/my-project"
    namespace = "code-helper"
    vector_db_url = "http://vector-db:8000"
    ingest_image = "code-helper-ingest:latest"

    with patch("crew_api.ingest_job.BatchV1Api") as mock_api_class:
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Trigger lifespan so app.state.settings exists, then override for test
            await client.get("/health")
            app.state.settings = CrewApiSettings(
                k8s_namespace=namespace,
                vector_db_url=vector_db_url,
                ingest_image=ingest_image,
            )
            response = await client.post("/project", json={"project_path": project_path})

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "accepted"
    assert "job_id" in data
    assert data["job_id"].startswith("ingest-")

    mock_api.create_namespaced_job.assert_called_once()
    call_kwargs = mock_api.create_namespaced_job.call_args[1]
    assert call_kwargs["namespace"] == namespace
    job = call_kwargs["body"]
    assert job.metadata.name == data["job_id"]
    containers = job.spec.template.spec.containers
    assert len(containers) == 1
    container = containers[0]
    assert container.image == ingest_image
    assert project_path in container.args
    # VECTOR_DB_URL in env
    env_names = [e.name for e in container.env]
    assert "VECTOR_DB_URL" in env_names
