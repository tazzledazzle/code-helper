"""Chat handler: build crew inputs, run kickoff, return response."""

from crew_api.crew import create_crew


def handle_chat(
    message: str,
    project_path: str | None = None,
    pinned_repo: str | None = None,
    attachments: list | None = None,
) -> dict:
    """Run crew with message (and optional project_path, pinned_repo, attachments); return response dict."""
    inputs: dict = {"message": message}
    if project_path is not None:
        inputs["project_path"] = project_path
    if pinned_repo is not None:
        inputs["pinned_repo"] = pinned_repo
    if attachments is not None:
        inputs["attachments"] = attachments

    crew = create_crew()
    result = crew.kickoff(inputs=inputs)

    response_text = result.raw or getattr(result, "final_output", "") or ""
    out: dict = {"response": response_text}
    if hasattr(result, "sources") and result.sources:
        out["sources"] = result.sources
    return out
