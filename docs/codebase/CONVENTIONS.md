# Coding Conventions

**Analysis Date:** 2025-02-20

## Naming Patterns

**Files:**
- Python: lowercase with underscores (`runner_client.py`, `ingest_job.py`, `rag_tool.py`). One main module per purpose; tools in `crew_api/crew/tools/` with `<name>_tool.py` or `stubs.py`.

**Functions:**
- snake_case: `run_ingest`, `chunk_directory`, `_validate_project_path`, `_default_runner_url`, `handle_chat`, `create_crew`. Private/helper prefixed with `_` where used (e.g. `_ingest_config`, `_run_summary`).

**Variables:**
- snake_case: `project_path`, `vector_db_url`, `collection_id`, `embed_func`, `chroma_client`. Type hints used in signatures (e.g. `str | None`, `list[str]`).

**Types:**
- Pydantic models: PascalCase (`ProjectPostBody`, `ChatPostBody`, `ExecuteRequest`, `ExecuteResponse`, `RAGToolInput`). Classes for agents/tools: PascalCase (`RAGTool`, `RunnerTool`, `SearchTool`, `StubCodeTool`).

## Code Style

**Formatting:**
- No dedicated formatter config file (no .prettierrc, no ruff.toml in code-helper). Indentation is 4 spaces; line length not strictly enforced in config.

**Linting:**
- .gitignore references `.mypy_cache`; no eslint or ruff config in repo. Imports are standard library first, then third-party, then local (see below).

## Import Organization

**Order:**
1. Standard library (os, sys, argparse, subprocess, tempfile, hashlib, time, asyncio, etc.)
2. Third-party (fastapi, pydantic, httpx, chromadb, crewai, kubernetes, pytest, unittest.mock)
3. Local packages: `from crew_api ...`, `from ingest ...`, `from runner ...`

**Path Aliases:**
- None. Imports use package names as in pyproject.toml (crew_api, runner, ingest, cli).

## Error Handling

**Patterns:**
- Runner: raise `HTTPException(status_code=400, detail={...})` for validation; custom `http_exception_handler` returns JSON with `error` and `code` for 400 invalid_input.
- crew_api: Pydantic validation for bodies; `response.raise_for_status()` in runner_client and CLI; no global exception handler.
- Ingest: raise `NotADirectoryError`, `ValueError`; in _main print to stderr and `sys.exit(1)`.
- Tests: patch/mock to avoid real K8s/network; stub LLMs and execute_sync to isolate behavior.

## Logging

**Framework:** No dedicated logging setup; standard library logging or print not heavily used in mapped code. Rely on uvicorn/FastAPI default request logging.

**Patterns:**
- No consistent log levels or correlation IDs. For new code, use `logging` with appropriate levels if adding observability.

## Comments

**When to Comment:**
- Docstrings on public functions and classes (e.g. `"""Runner base URL from env RUNNER_URL or RUNNER_SERVICE_URL."""`, module-level one-liners). Inline comments for non-obvious logic (e.g. Chroma list-of-lists in RAG tool).

**JSDoc/TSDoc:**
- Not used (chat_ui is vanilla JS with brief inline comments).

## Function Design

**Size:** Functions are generally single-purpose and short (e.g. _validate_project_path, _validate_command, _run_summary). Largest modules are `crew_api/app.py` and `runner/app.py` (routing + validation).

**Parameters:** Optional injection for testability (e.g. `client=`, `embed_func=`, `runner_url=`, `execute_sync=`, `transport=`). Use `*` to separate positional from keyword-only where appropriate (e.g. `run_ingest(..., *, client=..., embed_func=...)`).

**Return Values:** Dicts for API responses (e.g. `{"status": "ok"}`, `{"response": ...}`, `{"exit_code": ..., "stdout": ...}`). Pydantic models for Runner (ExecuteResponse). Crew returns CrewOutput (raw, final_output, sources).

## Module Design

**Exports:** Packages expose main callables (e.g. app in crew_api.app, create_crew in crew_api.crew, run_ingest in ingest.run). Tools exported via `crew_api/crew/tools/__init__.py` (RAGTool, RunnerTool, SearchTool, stubs).

**Barrel Files:** `__init__.py` are minimal or empty; tools package has explicit imports in `__init__.py` for crew agents to use.

---

*Convention analysis: 2025-02-20*
