"""Client for the Runner service (POST /execute)."""

import os
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _default_runner_url() -> str:
    """Runner base URL from env RUNNER_URL or RUNNER_SERVICE_URL."""
    return os.environ.get("RUNNER_URL") or os.environ.get("RUNNER_SERVICE_URL") or "http://runner:8080"


def _retry_if_transient(exc: BaseException) -> bool:
    """Retry on connection/timeout or 5xx."""
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


@retry(
    retry=retry_if_exception(_retry_if_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=1, max=4),
    reraise=True,
)
async def execute(
    project_path: str,
    command: list[str],
    runner_url: str | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    request_id: str | None = None,
) -> dict:
    """
    Call Runner service POST /execute. Returns dict with exit_code, stdout, stderr, duration_seconds.
    Bounded retries (3 attempts) on transient failures (connect, timeout, 5xx).
    """
    base_url = (runner_url or _default_runner_url()).rstrip("/")
    payload: dict = {"project_path": project_path, "command": command}
    if cwd is not None:
        payload["cwd"] = cwd
    if env is not None:
        payload["env"] = env
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds

    headers: dict[str, str] = {}
    if request_id is not None:
        headers["X-Request-Id"] = request_id

    if transport is not None:
        async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=60.0) as client:
            response = await client.post("/execute", json=payload, headers=headers)
    else:
        async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
            response = await client.post("/execute", json=payload, headers=headers)

    response.raise_for_status()
    return response.json()
