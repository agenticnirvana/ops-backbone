# Design 1 — Phase & Port Map (Chroma + Loki + Prometheus + Langfuse)

| Phase | Section | Tool | Host port | Status |
|-------|---------|------|-----------|--------|
| 1 | Alerts | Alertmanager | 9093 | ✅ |
| 1 | Webhook adapter | alert-receiver | 8090 | ✅ |
| 1 | Logs | **Loki** | 3100 | ✅ |
| 1 | Log shipper | **Promtail** | — | ✅ |
| 1 | Metrics | **Prometheus** | 9090 | ✅ |
| 1 | Dashboards | **Grafana** | 3001 | ✅ |
| 1 | **Vector DB** | **ChromaDB** | shared volume | ✅ |
| 1 | **Ingestion service** | **runbook-ingestion** | 8092 | ✅ |
| 1 | Ingestion | On-demand API + midnight Drive cron | — | ✅ |
| 2 | Agent | LangGraph | 8002 | ✅ |
| 2 | Gateway | platform UI | 8080 | ✅ |
| 2 | LLM | Ollama | 11434 | ✅ |
| 3 | LLM ops | **Langfuse** | 3000 | ✅ |
| 3 | Experiments | **MLflow** | 5001 | ✅ |
| 3 | OTEL | **OTEL Collector** | 4318 | ✅ |
| 4 | Policy | **OPA** | 8181 | ✅ |
| 4 | Validation | FastAPI guardrails | in-agent | ✅ |
| 5 | Tickets | PostgreSQL ticket-api | 8091 / 5432 | ✅ |
| 5 | CI | GitHub Actions | — | ✅ |

**Deploy:** [`deploy/deploy.sh`](deploy/deploy.sh) · **Guide:** [`IMPLEMENTATION.md`](IMPLEMENTATION.md)

**Env highlights:** `CHROMA_COLLECTION`, `LOKI_URL`, `PROMETHEUS_URL`, `LANGFUSE_*`, `MLFLOW_TRACKING_URI`, `OPA_URL`
