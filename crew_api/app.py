"""FastAPI app for the crew API."""

import asyncio
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from crew_api import runner_client
from crew_api.chat import handle_chat
from crew_api import ingest_job
from crew_api.config import CrewApiSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize settings and in-memory state; optionally validate Runner and Chroma at startup."""
    settings = CrewApiSettings()
    app.state.settings = settings

    if settings.validate_startup:
        runner_status = await _check_runner(settings.runner_url.rstrip("/"))
        if runner_status != "ok":
            print(
                f"Startup validation failed: Runner unreachable at {settings.runner_url} ({runner_status})",
                file=sys.stderr,
            )
            sys.exit(1)
        if settings.vector_db_url:
            chroma_status = await _check_chroma(settings.vector_db_url.rstrip("/"))
            if chroma_status != "ok":
                print(
                    f"Startup validation failed: Chroma unreachable at {settings.vector_db_url} ({chroma_status})",
                    file=sys.stderr,
                )
                sys.exit(1)

    app.state.project_path = None
    app.state.pinned_repo = None
    app.state.index_status = "idle"
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """Health check endpoint (liveness; process-only)."""
    return {"status": "ok"}


READINESS_TIMEOUT = 5.0


def _get_settings(request: Request) -> CrewApiSettings:
    """Settings from app state; lazy-init if lifespan did not run (e.g. some test clients)."""
    if not hasattr(request.app.state, "settings") or request.app.state.settings is None:
        request.app.state.settings = CrewApiSettings()
    return request.app.state.settings


def _runner_url(request: Request) -> str:
    return _get_settings(request).runner_url.rstrip("/")


def _vector_db_url(request: Request) -> str:
    return _get_settings(request).vector_db_url.rstrip("/")


def _llm_url(request: Request) -> str:
    return _get_settings(request).llm_url.rstrip("/")


async def _check_runner(base_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=READINESS_TIMEOUT) as client:
            r = await client.get(f"{base_url}/health")
            r.raise_for_status()
            return "ok"
    except httpx.TimeoutException:
        return "timeout"
    except (httpx.ConnectError, httpx.HTTPError):
        return "connection_error"
    except Exception:
        return "error"


async def _check_chroma(base_url: str) -> str:
    if not base_url:
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=READINESS_TIMEOUT) as client:
            r = await client.get(f"{base_url}/api/v2/heartbeat")
            r.raise_for_status()
            return "ok"
    except httpx.TimeoutException:
        return "timeout"
    except (httpx.ConnectError, httpx.HTTPError):
        return "connection_error"
    except Exception:
        return "error"


async def _check_llm(base_url: str, health_path: str | None) -> str:
    if not base_url:
        return "not_configured"
    path = health_path or "/"
    try:
        async with httpx.AsyncClient(timeout=READINESS_TIMEOUT) as client:
            r = await client.get(f"{base_url}{path}")
            r.raise_for_status()
            return "ok"
    except httpx.TimeoutException:
        return "timeout"
    except (httpx.ConnectError, httpx.HTTPError):
        return "connection_error"
    except Exception:
        return "error"


@app.get("/readyz")
async def readyz(request: Request):
    """Readiness: Runner + Chroma + LLM (parallel, 5s timeout each)."""
    runner_base = _runner_url(request)
    chroma_base = _vector_db_url(request)
    llm_base = _llm_url(request)
    llm_health_path = _get_settings(request).llm_health_path

    runner_task = _check_runner(runner_base)
    chroma_task = _check_chroma(chroma_base)
    llm_task = _check_llm(llm_base, llm_health_path)

    runner_status, chroma_status, llm_status = await asyncio.gather(runner_task, chroma_task, llm_task)
    ready = runner_status == "ok" and chroma_status == "ok" and llm_status == "ok"
    body = {
        "ready": ready,
        "runner": runner_status,
        "chroma": chroma_status,
        "llm": llm_status,
    }
    status_code = 200 if ready else 503
    return JSONResponse(status_code=status_code, content=body)


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
    """Namespace, vector_db_url, and ingest image from settings."""
    s = _get_settings(request)
    return s.k8s_namespace, s.vector_db_url, s.ingest_image


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

    runner_url = _get_settings(request).runner_url
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
