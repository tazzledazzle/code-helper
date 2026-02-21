"""Chat handler: build crew inputs, run kickoff, return response."""

import time
import structlog

from crew_api.crew import create_crew


def _step_names_from_result(result) -> list[str]:
    """Extract task/step names from CrewOutput.tasks_output (safe, no PII)."""
    steps: list[str] = []
    tasks_output = getattr(result, "tasks_output", None) or []
    for t in tasks_output:
        name = getattr(t, "name", None) or getattr(t, "description", None)
        if name is not None:
            steps.append(str(name)[:200])
    return steps


def handle_chat(
    message: str,
    project_path: str | None = None,
    pinned_repo: str | None = None,
    attachments: list | None = None,
    request_id: str | None = None,
) -> dict:
    """Run crew with message (and optional project_path, pinned_repo, attachments); return response dict."""
    inputs: dict = {"message": message}
    if project_path is not None:
        inputs["project_path"] = project_path
    if pinned_repo is not None:
        inputs["pinned_repo"] = pinned_repo
    if attachments is not None:
        inputs["attachments"] = attachments

    start = time.perf_counter()
    crew = create_crew()
    result = crew.kickoff(inputs=inputs)
    duration_seconds = round(time.perf_counter() - start, 3)

    step_names = _step_names_from_result(result)
    structlog.get_logger().info(
        "crew_run_summary",
        request_id=request_id,
        outcome="success",
        duration_seconds=duration_seconds,
        steps=step_names,
    )

    response_text = result.raw or getattr(result, "final_output", "") or ""
    out: dict = {"response": response_text}
    if hasattr(result, "sources") and result.sources:
        out["sources"] = result.sources
    return out
