# Failure Modes & Assumptions

Per-failure runbooks, how to interpret healthy vs broken state, and operational assumptions. Main runbook: [RUNBOOK.md](RUNBOOK.md). Config and state: [CONFIG.md](CONFIG.md), [STATE.md](STATE.md).

---

## Per-failure runbooks

### Crew API 5xx or timeouts

**When to use:** Clients get 5xx from Crew API, or requests time out (e.g. POST /chat or POST /run never return).

**Steps:**
1. Check Crew API logs (structured JSON); use `request_id` to trace the failing request.
2. Confirm Runner is reachable from Crew API: `curl -s -o /dev/null -w "%{http_code}" http://<RUNNER_URL>/health` (expect 200). Check [CONFIG.md](CONFIG.md) for `RUNNER_URL` and timeouts (Runner call: 60s).
3. Confirm Chroma is reachable: Crew API uses `VECTOR_DB_URL`; if readiness fails, Chroma or LLM may be down.
4. Check **GET /metrics** on Crew API for request count and latency by route; identify which route is failing or slow.

**Verification:** **GET /health** returns 200; **GET /readyz** returns 200 when Runner, Chroma, and (if configured) LLM are up. Retry the failing operation.

**Escalation:** If dependencies are up but 5xx persist, inspect stack traces in logs (request_id). Consider enabling `CREW_API_VALIDATE_DEPS=1` so startup fails fast if deps are unreachable next time. For timeouts, consider increasing timeouts (CONFIG.md) or optimizing the operation.

---

### Runner timeouts or errors

**When to use:** POST /run or Runner POST /execute times out, or returns 4xx/5xx; or commands fail with unexpected exit codes.

**Steps:**
1. Check Runner **GET /health** (e.g. `curl http://<runner>/health`). If 5xx, Runner process may be down or overloaded.
2. Confirm `project_path` is under **ALLOWED_ROOT** (Runner returns 400 if not). See [CONFIG.md](CONFIG.md).
3. Confirm the command is allowlisted (Runner rejects commands whose executable is not in the allowlist). Check Runner logs for validation errors.
4. If the request times out: Runner has a 60s timeout for execution; long-running commands may need to be split or run outside the Runner.

**Verification:** **POST /execute** with a simple allowlisted command (e.g. `["python","-c","print(1)"]`) and a path under ALLOWED_ROOT returns 200 with `exit_code`, `stdout`, `stderr`, `duration_seconds`.

**Escalation:** Runner logs; check disk/CPU on the Runner host; consider increasing timeout in crew_api or fixing the command. Document that Runner runs arbitrary code under ALLOWED_ROOT—ensure ALLOWED_ROOT is constrained.

---

### Chroma down or empty index

**When to use:** GET /readyz returns 503 (Chroma unreachable); or RAG returns no/empty results after indexing; or Chroma container/pod is not running.

**Steps:**
1. Restart Chroma: Compose `docker compose restart chroma`; K8s restart the Chroma deployment (e.g. `kubectl rollout restart deployment/vector-db -n code-helper`).
2. Verify Chroma is reachable from Crew API (same network/DNS). Check `VECTOR_DB_URL` in [CONFIG.md](CONFIG.md).
3. If the Chroma volume was lost or recreated, the index is empty. Re-index: **POST /project** with the desired `project_path`, then poll **GET /project** until `index_status` is `ready`. See [STATE.md](STATE.md).

**Verification:** **GET /readyz** on Crew API returns 200 (when Chroma and Runner and LLM are up). **GET /project** shows `index_status`; after re-index, chat/RAG should return results.

**Escalation:** Chroma logs and disk/volume; ensure Chroma data volume is persisted (Compose: named volume; K8s: PVC). If Chroma is external, check network and auth.

---

### Ingest stuck or 409

**When to use:** `index_status` stays "indexing" for a long time; or POST /project returns 409 "already_indexing"; or ingest Job is failing in the cluster.

**Steps:**
1. **GET /project** refreshes status from the Kubernetes Job when status is "indexing". Poll a few times; if it moves to `ready` or `failed`, no further action needed.
2. If it stays "indexing", inspect the Job: `kubectl get jobs -n code-helper`, then `kubectl logs -n code-helper job/<job_id> -f`. Job name is stable per project: `ingest-<8-char-hash>`. See [STATE.md](STATE.md).
3. Check Job pod: `kubectl get pods -n code-helper -l job-name=<job_id>`. If CrashLoopBackOff or Error, read pod logs and events. Confirm `VECTOR_DB_URL` and project path (args) are correct for the ingest image.
4. On **409**: Another request already started indexing that project. Use the returned `job_id` to watch the same Job; do not create a second Job. Wait for completion or for the existing Job to fail, then re-POST if needed.
5. To force a retry after a failed Job: POST /project is idempotent for completed Jobs (returns existing job_id). To run ingest again for the same project, you can delete the completed Job and POST /project again, or rely on idempotent 200 with same job_id.

**Verification:** **GET /project** shows `index_status` `ready` or `failed`. If `ready`, RAG queries should work. If `failed`, fix the cause (e.g. Chroma unreachable from Job, bad path) and re-run (delete Job + POST /project or fix and create new Job per your workflow).

**Escalation:** Ingest pod logs and K8s events; confirm ingest image has correct `VECTOR_DB_URL` and network to Chroma. For 409, no second Job is created—operate on the single Job per project.

---

## Healthy vs broken state

| Component   | Healthy                                                                 | Broken                                                                 |
|------------|--------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **Crew API** | GET /health 200; GET /readyz 200 when deps up; POST /chat and /run return 2xx within timeout. | GET /health 5xx or process down; GET /readyz 503 (deps down); POST /chat or /run 5xx or timeout. |
| **Runner**   | GET /health 200; POST /execute returns 200 with exit_code for allowlisted commands under ALLOWED_ROOT. | GET /health 5xx or unreachable; POST /execute 400 (path/command invalid) or timeout; subprocess errors. |
| **Chroma**   | Reachable at VECTOR_DB_URL; Crew API readiness passes; collections can be queried. | Unreachable (readiness 503); empty or missing collection after volume loss; 5xx from Chroma. |
| **Ingest**   | K8s Job exists for project; Job completes (succeeded → index_status ready; failed → index_status failed); GET /project reflects status. | Job stuck (active indefinitely); Job failed (check logs); POST /project 409 when Job already active; index_status never leaves "indexing" due to refresh/Job issue. |

Use the runbooks above when a component is in a broken state; verification steps above confirm return to healthy.

---

## Assumptions

### Single-replica

- The system is designed for **single-replica** operation of Crew API (and typically Runner). In-memory state in Crew API (project_path, index_status) is **not shared** across replicas. Running multiple Crew API replicas will result in each replica having its own view of project/index state; GET /project can still refresh from K8s when project_path is set on that replica.
- For multi-replica or HA, you would need external state (e.g. Redis or DB) and is out of scope for this runbook.

### In-memory state

- **Crew API** holds `project_path`, `pinned_repo`, and `index_status` in **in-memory** `app.state`. After a **process restart**, this state is lost (e.g. GET /project may show no project / idle). See [STATE.md](STATE.md).
- Recovery: Caller can **POST /project** again with the same path; if the ingest Job still exists in K8s, API returns idempotent 200 with existing job_id or 409 if Job is still active. GET /project refreshes status from K8s when `index_status` is "indexing" and `project_path` is set—so after restart, set project again via POST to re-establish state on that instance.

### Disable / rollback

- **Disable:** Stop the stack: Docker Compose `docker compose down`; Kubernetes delete namespace or scale deployments to 0. Crew API and Runner stop; Chroma data persists if volume is retained.
- **Rollback:** Deploy a previous image version of crew_api, runner, or ingest (same process as deploy; use your CI/CD or `kubectl set image`). No schema migrations; config is env-based (CONFIG.md). If **Chroma** was recreated or volume lost, **re-index** after rollback: POST /project and wait for ready.
