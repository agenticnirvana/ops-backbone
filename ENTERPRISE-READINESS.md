# Design 1 — Enterprise Readiness

Audit of **architecture-design-1** against the agreed five-phase SRE AgentOps architecture.

## Architecture alignment

| Phase | Planned (diagram) | Implemented | Notes |
|-------|-------------------|-------------|-------|
| **1 Ingestion** | Alertmanager, Loki, Promtail, Prometheus, Grafana, Chroma, **reindex job** | ✅ | `runbook-ingestion` service on `:8092` |
| **2 Orchestration** | LangGraph, gateway, MCP, Ollama | ✅ | Graph includes metrics node |
| **3 Evaluation** | Langfuse, MLflow, OTEL | ✅ | OTEL collector → debug exporter (Langfuse via SDK) |
| **4 Guardrails** | OPA, HITL, FastAPI guardrails | ✅ | Rego policy on execute; **Slack HITL notify** (optional webhook) |
| **5 Action** | PostgreSQL tickets, GitHub Actions | ✅ | `ticket-api` + CI workflow |

## Enterprise runbook ingestion pipeline

Separate from the agent — **do not bake vectors into agent images**.

```
Google Drive folder ──► sync (incremental) ──► /data/runbooks
Git seed runbooks   ──► bootstrap copy      ──► /data/runbooks
                              │
                              ▼
                   runbook-ingestion :8092
                     • POST /v1/ingest/reindex   (on demand)
                     • POST /v1/ingest/sync-drive
                     • GET  /v1/ingest/status
                     • cron 0 0 * * * UTC        (midnight incremental)
                              │
                              ▼
                   Chroma volume (shared)
                     • full rebuild → new collection + active.json alias swap
                     • incremental → upsert changed runbooks only
                              │
                              ▼
                   agent / gateway read active collection
```

### Operations

```bash
# On-demand incremental reindex (+ Drive sync if enabled)
./deploy.sh reindex incremental

# Full rebuild (alias swap to new collection)
./deploy.sh reindex full

# Check active index + last job
curl -H "Authorization: Bearer $INGESTION_API_TOKEN" http://localhost:8092/v1/ingest/status
```

### Google Drive

1. Create a folder with `*.md` SRE runbooks
2. Add service account JSON to `deploy/secrets/google-service-account.json`
3. Share folder with service account email
4. Set `GOOGLE_DRIVE_ENABLED=true` and `GOOGLE_DRIVE_FOLDER_ID` in `.env`

Midnight cron (`RUNBOOK_CRON_SCHEDULE`, default `0 0 * * *` UTC) runs **Drive sync + incremental reindex**.

## Remaining gaps (non-blocking for local course)

| Gap | Priority | Recommendation |
|-----|----------|----------------|
| Slack interactive Approve button (callback) | Low | Current webhook posts link to OpsPilot; optional Slack Bolt app |
| OTEL collector → Langfuse OTLP exporter | Medium | Wire `otlphttp` exporter with Langfuse auth headers |
| Langfuse eval datasets wired to eval gate | Medium | Phase 3 lab — push golden alerts as dataset |
| Alertmanager → agent auto-route in demo | Low | Prometheus alert fires → webhook (config exists) |
| HA / K8s manifests for Design 1 | Later | Wave 5 — mirror compose stack in Helm |

## Production coding standards applied

- Shared **Chroma volume** — no index baked into Docker images
- **Job tracking** in PostgreSQL (`ingestion_jobs`, `runbook_sources`)
- **API token auth** on ingestion endpoints
- **Atomic alias swap** via `active.json` manifest
- **Incremental indexing** by content hash
- **Single-flight** job lock (one ingestion at a time)
- **SRE-only** runbook corpus (no HR/internal domains)

See [`IMPLEMENTATION.md`](IMPLEMENTATION.md) · [`phases/01-ingestion.md`](phases/01-ingestion.md)
