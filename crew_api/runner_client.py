"""Client for the Runner service (POST /execute)."""

import os
import httpx


def _default_runner_url() -> str:
    """Runner base URL from env RUNNER_URL or RUNNER_SERVICE_URL."""
    return os.environ.get("RUNNER_URL") or os.environ.get("RUNNER_SERVICE_URL") or "http://runner:8080"


async def execute(
    project_path: str,
    command: list[str],
    runner_url: str | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """
    Call Runner service POST /execute. Returns dict with exit_code, stdout, stderr, duration_seconds.
    """
    base_url = (runner_url or _default_runner_url()).rstrip("/")
    payload: dict = {"project_path": project_path, "command": command}
    if cwd is not None:
        payload["cwd"] = cwd
    if env is not None:
        payload["env"] = env
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds

    if transport is not None:
        async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=60.0) as client:
            response = await client.post("/execute", json=payload)
    else:
        async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
            response = await client.post("/execute", json=payload)

    response.raise_for_status()
    return response.json()
