"""FastAPI app for the runner service: POST /execute to run commands in a project."""

import os
import subprocess
import time
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from prometheus_fastapi_instrumentator import Instrumentator

from runner.config import RunnerSettings
from runner.logging_config import configure_logging

ALLOWED_COMMAND_PREFIXES = ("pytest", "npm", "cargo", "go", "python", "node")

_runner_settings: RunnerSettings | None = None


def _get_runner_settings() -> RunnerSettings:
    global _runner_settings
    if _runner_settings is None:
        _runner_settings = RunnerSettings()
    return _runner_settings


class ExecuteRequest(BaseModel):
    """Request body for POST /execute."""

    project_path: str
    command: list[str]
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout_seconds: int | None = Field(default=300, ge=1)


class ExecuteResponse(BaseModel):
    """Response body for POST /execute."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


configure_logging()
app = FastAPI(title="Runner", version="0.1.0")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Read or generate X-Request-Id; bind to structlog contextvars; add to response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()


app.add_middleware(RequestIdMiddleware)


@app.get("/health")
def health():
    """Process-only health; no test execution."""
    return {"status": "ok"}


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return 400 invalid_input with body {"error": "...", "code": "invalid_input"}."""
    if exc.status_code == 400 and isinstance(exc.detail, dict) and exc.detail.get("code") == "invalid_input":
        return JSONResponse(
            status_code=400,
            content={"error": exc.detail.get("error", ""), "code": "invalid_input"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log full trace server-side; return 500 with JSON only (no stack trace)."""
    structlog.get_logger().exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An internal error occurred."},
    )


def _validate_project_path(project_path: str) -> None:
    """Raise HTTPException 400 if project_path is not under ALLOWED_ROOT."""
    allowed_root = os.path.realpath(_get_runner_settings().allowed_root)
    try:
        resolved = os.path.realpath(project_path)
    except OSError:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid or inaccessible project_path", "code": "invalid_input"},
        )
    try:
        if os.path.commonpath([resolved, allowed_root]) != allowed_root:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "project_path must be under ALLOWED_ROOT",
                    "code": "invalid_input",
                },
            )
    except ValueError:
        # paths on different drives (e.g. Windows)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "project_path must be under ALLOWED_ROOT",
                "code": "invalid_input",
            },
        )


def _validate_command(command: list[str]) -> None:
    """Raise HTTPException 400 if command is empty or not in allowlist."""
    if not command:
        raise HTTPException(
            status_code=400,
            detail={"error": "command cannot be empty", "code": "invalid_input"},
        )
    exe = os.path.basename(command[0]).lower()
    allowed = any(
        exe == p or exe.startswith(p) for p in ALLOWED_COMMAND_PREFIXES
    )
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "command executable not in allowlist",
                "code": "invalid_input",
            },
        )


@app.post("/execute", response_model=ExecuteResponse)
def execute(body: ExecuteRequest) -> ExecuteResponse:
    """Run a command in the given project path. Returns exit_code, stdout, stderr, duration_seconds."""
    _validate_project_path(body.project_path)
    _validate_command(body.command)

    workdir = body.cwd if body.cwd is not None else body.project_path
    timeout = body.timeout_seconds if body.timeout_seconds is not None else 300
    env: dict[str, str] | None = None
    if body.env is not None:
        env = {**os.environ, **body.env}

    start = time.perf_counter()
    try:
        result = subprocess.run(
            body.command,
            cwd=workdir,
            env=env,
            capture_output=True,
            timeout=timeout,
            text=False,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.perf_counter() - start
        return ExecuteResponse(
            exit_code=-1,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=(e.stderr.decode() if e.stderr else "") + " (timeout)",
            duration_seconds=round(elapsed, 3),
        )
    elapsed = time.perf_counter() - start

    return ExecuteResponse(
        exit_code=result.returncode,
        stdout=result.stdout.decode() if result.stdout else "",
        stderr=result.stderr.decode() if result.stderr else "",
        duration_seconds=round(elapsed, 3),
    )


Instrumentator(
    excluded_handlers=["/metrics"],
    should_ignore_untemplated=True,
).instrument(app).expose(app)
