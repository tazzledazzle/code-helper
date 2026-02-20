"""FastAPI app for the crew API."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel

from crew_api import runner_client
from crew_api.chat import handle_chat
from crew_api import ingest_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize in-memory state for project and index status."""
    app.state.project_path = None
    app.state.pinned_repo = None
    app.state.index_status = "idle"
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


class ProjectPostBody(BaseModel):
    """Body for POST /project."""

    project_path: str
    pinned_repo: str | None = None


@app.get("/project")
def get_project(request: Request):
    """Return current project path, pinned repo, and index status."""
    return {
        "project_path": getattr(request.app.state, "project_path", None),
        "pinned_repo": getattr(request.app.state, "pinned_repo", None),
        "index_status": getattr(request.app.state, "index_status", "idle"),
    }


def _ingest_config(request: Request):
    """Namespace, vector_db_url, and ingest image from app state or env."""
    namespace = getattr(request.app.state, "k8s_namespace", None) or os.environ.get("K8S_NAMESPACE", "code-helper")
    vector_db_url = getattr(request.app.state, "vector_db_url", None) or os.environ.get("VECTOR_DB_URL", "")
    image = getattr(request.app.state, "ingest_image", None) or os.environ.get("INGEST_IMAGE", "code-helper-ingest")
    return namespace, vector_db_url, image


@app.post("/project")
def post_project(request: Request, body: ProjectPostBody):
    """Set project path (and optional pinned_repo), create ingest Job, set index_status to indexing, return accepted and job_id."""
    request.app.state.project_path = body.project_path
    request.app.state.pinned_repo = body.pinned_repo
    request.app.state.index_status = "indexing"
    namespace, vector_db_url, image = _ingest_config(request)
    job_name = ingest_job.create(
        project_path=body.project_path,
        namespace=namespace,
        vector_db_url=vector_db_url,
        image=image,
    )
    return {"status": "accepted", "job_id": job_name}


# --- POST /chat (Crew kickoff) ---


class ChatPostBody(BaseModel):
    """Body for POST /chat."""

    message: str
    project_path: str | None = None
    pinned_repo: str | None = None
    attachments: list | None = None


@app.post("/chat")
def post_chat(request: Request, body: ChatPostBody):
    """Run crew with message; return response and optional sources."""
    result = handle_chat(
        message=body.message,
        project_path=body.project_path,
        pinned_repo=body.pinned_repo,
        attachments=body.attachments,
    )
    return result


# --- POST /run (Runner integration) ---

RUN_TESTS_COMMAND = ["pytest"]


class RunPostBody(BaseModel):
    """Body for POST /run."""

    project_path: str
    action: str  # e.g. "run_tests", "verify"
    command: list[str] | None = None


def _run_summary(exit_code: int, stdout: str) -> str:
    """Derive a short summary from exit_code and stdout."""
    if exit_code == 0:
        return stdout.strip() or "Tests passed"
    return stdout.strip() or f"Exit code {exit_code}"


@app.post("/run")
async def post_run(request: Request, body: RunPostBody):
    """Run a command via the Runner service; action run_tests defaults to pytest."""
    command = body.command
    if body.action == "run_tests" and command is None:
        command = RUN_TESTS_COMMAND
    if command is None:
        command = RUN_TESTS_COMMAND  # fallback for "verify" without command

    runner_url = getattr(request.app.state, "runner_url", None)
    runner_transport = getattr(request.app.state, "runner_transport", None)

    result = await runner_client.execute(
        project_path=body.project_path,
        command=command,
        runner_url=runner_url,
        transport=runner_transport,
    )

    exit_code = result["exit_code"]
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    duration_seconds = result.get("duration_seconds", 0.0)

    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "summary": _run_summary(exit_code, stdout),
        "stdout": stdout,
        "stderr": stderr,
        "duration_seconds": duration_seconds,
    }
