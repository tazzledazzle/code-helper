# Testing Patterns

**Analysis Date:** 2025-02-20

## Test Framework

**Runner:**
- pytest with pytest-asyncio (asyncio_mode: auto).
- Config: `code-helper/pyproject.toml` ([tool.pytest.ini_options] testpaths = ["tests"], pythonpath = ["."]).

**Assertion Library:**
- Built-in assert; no separate assertion library.

**Run Commands:**
```bash
pytest                    # Run all tests (from code-helper root)
pytest tests/             # Same
pytest -v                 # Verbose
pytest tests/test_runner.py   # Single file
```
Watch and coverage: no script in repo; use `pytest --cov` if pytest-cov is installed.

## Test File Organization

**Location:**
- Single top-level `tests/` directory; tests are not co-located next to each package.

**Naming:**
- `test_<package>_<area>.py` or `test_<module>_<area>.py`: e.g. `test_crew_api_health.py`, `test_crew_api_chat.py`, `test_runner.py`, `test_ingest_run.py`, `test_rag_tool.py`.

**Structure:**
```
tests/
  test_crew_api_health.py
  test_crew_api_chat.py
  test_crew_api_run.py
  test_crew_api_project.py
  test_crew_api_ingest_job.py
  test_crew_crew.py
  test_runner.py
  test_ingest_run.py
  test_ingest_chunk.py
  test_ingest_vector_store.py
  test_rag_tool.py
  test_runner_tool.py
  test_search_tool.py
```

## Test Structure

**Suite Organization:**
- One module per area; multiple `async def test_*` or `def test_*` per file. No nested class-based grouping.

**Patterns:**
- Setup: fixtures (e.g. `chroma_client`, `fake_embedding`, `sample_project`, `mock_ingest_job_create`); `monkeypatch` for env (e.g. ALLOWED_ROOT); `patch` for K8s or create_crew.
- Teardown: implicit (fixtures scope function); crew test restores CREWAI_STORAGE_DIR in finally.
- Assertions: assert on status_code, response.json() keys and values, string content, types.

Example (API test with mock):
```python
@pytest.mark.asyncio
async def test_post_chat_returns_200_with_response_string():
    mock_output = MagicMock()
    mock_output.raw = "Here is the explanation."
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = mock_output
    with patch("crew_api.chat.create_crew", return_value=mock_crew):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/chat", json={"message": "explain this"})
    assert response.status_code == 200
    assert response.json()["response"] == "Here is the explanation."
```

## Mocking

**Framework:** unittest.mock (patch, MagicMock); httpx.MockTransport and httpx.ASGITransport for in-process API tests.

**Patterns:**
- Patch at use site: `patch("crew_api.chat.create_crew", ...)`, `patch("crew_api.ingest_job.BatchV1Api")`.
- Inject test doubles: RunnerTool(execute_sync=fake_execute_sync); RAGTool(client=chroma_client, embedding_function=fake_embedding); run_ingest(..., client=chroma_client, embed_func=_mock_embed).
- Runner API tests: set app.state.runner_transport to httpx.MockTransport(handler) so POST /run does not hit real Runner.
- Crew: _StubLLM (BaseLLM returning fixed string) and create_crew(llm=stub_llm, manager_llm=stub_llm); CREWAI_STORAGE_DIR set to temp dir.

**What to Mock:**
- K8s API (BatchV1Api), create_crew, runner HTTP (transport), Ollama/Chroma in unit tests (embed_func, Chroma client).

**What NOT to Mock:**
- FastAPI app and request handling (test via ASGITransport); ingest chunk/vector_store logic when testing with in-memory Chroma and fake embeddings.

## Fixtures and Factories

**Test Data:**
- In-memory Chroma: `chromadb.EphemeralClient()` in fixture.
- Fake embeddings: class implementing EmbeddingFunction (e.g. 384-dim deterministic from hash) in test module or fixture.
- Sample project: `tmp_path` with (tmp_path / "a.py").write_text(...).
- Mock Runner response: dict with exit_code, stdout, stderr, duration_seconds.

**Location:**
- Fixtures defined in same test file or at top of file; no shared `conftest.py` in mapped code (conftest not present).

## Coverage

**Requirements:** No enforced coverage threshold in pyproject.toml.

**View Coverage:**
```bash
pytest --cov=crew_api --cov=runner --cov=ingest --cov=cli --cov-report=term-missing
```
(Requires pytest-cov.)

## Test Types

**Unit Tests:**
- Tools (RAG, Runner, Search) with injected clients/callbacks; ingest chunk and vector_store with EphemeralClient and fake embedding; crew create_crew and kickoff with stub LLM.

**Integration-style (in-process):**
- API tests via httpx.ASGITransport(app=app): /health, /project, /chat, /run, /execute with mocks for K8s and runner so no real network or cluster.

**E2E Tests:**
- Not present. No tests against real Runner, Chroma, or K8s cluster.

## Common Patterns

**Async Testing:**
- Use `@pytest.mark.asyncio` and `async def test_*`; async client with `async with httpx.AsyncClient(...)`.

**Error Testing:**
- Assert status_code (e.g. 400), response body (e.g. code == "invalid_input", "error" in data). Example: test_post_execute_rejects_project_path_outside_allowed_root, test_post_execute_rejects_command_not_in_allowlist.

**Isolating Crew:**
- Set CREWAI_STORAGE_DIR to temp dir; pass stub LLM to create_crew so no external LLM or disk beyond temp.

---

*Testing analysis: 2025-02-20*
