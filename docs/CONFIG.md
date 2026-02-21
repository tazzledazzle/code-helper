# Environment contract (Code Helper)

Single source of truth for environment variables used by Crew API, Runner, and Ingest. This document is the env contract for the runbook; see [RUNBOOK.md](RUNBOOK.md) for run, operate, and troubleshoot. All three apps use pydantic-settings; empty env values fall back to defaults.

| Env var | Service(s) | Required / optional | Default | Description |
|---------|------------|---------------------|--------|-------------|
| RUNNER_URL | Crew API | Optional | `http://runner:8080` | Runner service base URL (Crew API uses this for /run and readiness). |
| RUNNER_SERVICE_URL | Crew API | Optional | (same as RUNNER_URL) | Alternative env name for Runner URL; used if RUNNER_URL unset. |
| VECTOR_DB_URL | Crew API, Ingest | Optional | `""` | Chroma base URL (e.g. `http://chroma:8000`). Empty = in-memory for ingest; readiness treats as not_configured when empty. |
| CHROMA_URL | Ingest | Optional | (same as VECTOR_DB_URL) | Alternative env name for Chroma; used if VECTOR_DB_URL unset. |
| LLM_URL | Crew API | Optional | `""` | LLM base URL (Ollama or vLLM). Used for readiness and crew. |
| OPENAI_BASE_URL | Crew API | Optional | (same as LLM_URL) | Alternative env name for LLM URL (CrewAI convention). |
| LLM_HEALTH_PATH | Crew API | Optional | `None` (use `/`) | Path for LLM health check (e.g. `/health` for vLLM; default `/` for Ollama). |
| K8S_NAMESPACE | Crew API | Optional | `code-helper` | Kubernetes namespace for ingest Job creation. |
| INGEST_IMAGE | Crew API | Optional | `code-helper-ingest` | Docker image for the ingest Job. |
| CREW_API_VALIDATE_DEPS | Crew API | Optional | `0` / false | Set to `1`, `true`, or `yes` to validate Runner and Chroma at startup; process exits with clear error if unreachable. Default off. |
| ALLOWED_ROOT | Runner | Optional | `/tmp` | Root directory under which project_path must lie for POST /execute. |

## Timeouts (outbound calls)

| Call | Timeout | Notes |
|------|---------|--------|
| Runner POST /execute | 60s | `crew_api.runner_client` |
| Readiness (Runner, Chroma, LLM) | 5s each | `crew_api.app` `/readyz` |
| Search (Tavily/Serper) | 30s | `crew_api.crew.tools.search_tool` |
| Ingest embed (Ollama) | 60s | `ingest.embed` |
| Chroma HTTP client | — | chromadb `HttpClient` does not expose a request timeout in the public API; network timeouts depend on the environment. |
| CrewAI / LLM (chat) | — | Governed by CrewAI and the LLM server (e.g. Ollama); no per-call timeout configured in code-helper. |

## Notes

- **Crew API** reads config via `crew_api.config.CrewApiSettings`.
- **Runner** reads config via `runner.config.RunnerSettings`.
- **Ingest** reads config via `ingest.config.IngestSettings`.
- When `CREW_API_VALIDATE_DEPS=1`, startup fails fast if Runner or Chroma are unreachable; when unset, startup does not block.
