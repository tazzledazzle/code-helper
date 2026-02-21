# External Integrations

**Analysis Date:** 2025-02-20

## APIs & External Services

**Search (optional):**
- Tavily – `crew_api/crew/tools/search_tool.py`: POST to `https://api.tavily.com/search` when `TAVILY_API_KEY` is set.
- Serper – same module: POST to `https://google.serper.dev/search` when `SERPER_API_KEY` is set; stub message when neither key is set.

**Embeddings (optional):**
- Ollama-style embed API – `ingest/embed.py`: POST to configurable base URL (default `http://localhost:11434`) at `/api/embed` with model `nomic-embed-text`. Used by ingest pipeline when no `embed_func` is injected.

**LLM:**
- CrewAI uses env-configured LLM (e.g. OPENAI_BASE_URL or Ollama). K8s ConfigMap has `LLM_URL` (optional). No direct HTTP client to an LLM in the mapped code; configuration is via CrewAI.

## Data Storage

**Databases:**
- Chroma – vector store for RAG and ingest.
  - Connection: `VECTOR_DB_URL` or `CHROMA_URL` (crew_api, ingest).
  - Client: `chromadb.HttpClient` when URL is set (`ingest/run.py`), else in-memory / `EphemeralClient` in tests.
  - In Docker/K8s: service `chroma` at port 8000.

**File Storage:**
- Local filesystem: runner executes commands under `ALLOWED_ROOT`; ingest reads project directories. No object storage in codebase.

**Caching:**
- None. Chroma holds vector data only.

## Authentication & Identity

**Auth Provider:**
- None. No auth on crew_api or runner endpoints. Chat UI and CLI call APIs without credentials.

## Monitoring & Observability

**Error Tracking:**
- None.

**Logs:**
- Standard FastAPI/uvicorn logging; no centralized logging or tracing in code.

## CI/CD & Deployment

**Hosting:**
- Docker Compose (crew_api, runner, chroma; optional ollama). Kubernetes: namespace `code-helper`, deployments for crew-api, runner, chroma; Job template for ingest; ConfigMap for env.

**CI Pipeline:**
- Not detected in code-helper (no `.github/workflows` in code-helper; block-tor-exit-nodes has GitHub Actions).

## Environment Configuration

**Required env vars (by component):**
- crew_api: `RUNNER_URL` or `RUNNER_SERVICE_URL` (default `http://runner:8080`), `VECTOR_DB_URL`/`CHROMA_URL` for ingest Job and RAG; `K8S_NAMESPACE`, `INGEST_IMAGE` for Job creation.
- runner: `ALLOWED_ROOT` (default `/tmp`; path allowlist for `/execute`).
- ingest (Job): `VECTOR_DB_URL` or `CHROMA_URL`.
- CLI: `CODE_HELPER_API_URL` (default `http://localhost:8000`).
- Crew/tests: `CREWAI_STORAGE_DIR` (tests set to temp dir).
- Optional: `TAVILY_API_KEY`, `SERPER_API_KEY`, `LLM_URL`.

**Secrets location:**
- Not in repo. API keys and URLs are expected via environment (e.g. ConfigMap or host env); no secrets manager integration.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- crew_api → runner: POST `/execute` (via `crew_api/runner_client.py`).
- crew_api → Kubernetes API: create ingest Job (BatchV1Api in `crew_api/ingest_job.py`).
- Ingest → Chroma: HTTP client to `VECTOR_DB_URL`.
- Search tool → Tavily or Serper (when keys set).
- Embed → Ollama-style endpoint (when used).

---

*Integration audit: 2025-02-20*
