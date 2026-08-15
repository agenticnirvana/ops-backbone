# Phase 1 — Ingestion (Design 1)

**Tools:** Alertmanager · Promtail · **Loki** · **Prometheus** · Grafana · **ChromaDB** · **Runbook ingestion**

| Component | Port | Role |
|-----------|------|------|
| alert-receiver | 8090 | Webhook adapter |
| **runbook-ingestion** | **8092** | On-demand reindex + midnight Drive sync |
| Loki | 3100 | Log store |
| Prometheus | 9090 | Metrics |
| ChromaDB | shared volume | Runbook vectors (not baked in agent image) |

## Runbook ingestion pipeline

| Trigger | Behavior |
|---------|----------|
| **Bootstrap** | Seed git runbooks → full index on first start |
| **On demand** | `POST /v1/ingest/reindex` or `./deploy.sh reindex incremental` |
| **Midnight cron** | Google Drive folder sync → incremental reindex (`0 0 * * *` UTC) |

```bash
cd deploy && cp .env.example .env && ./deploy.sh up
curl -H "Authorization: Bearer $INGESTION_API_TOKEN" http://localhost:8092/v1/ingest/status
./deploy.sh reindex incremental
```

See [`../ENTERPRISE-READINESS.md`](../ENTERPRISE-READINESS.md) · [`../services/runbook-ingestion/`](../services/runbook-ingestion/)

**Live deploy:** [`deploy/`](deploy/) · [`IMPLEMENTATION.md`](../IMPLEMENTATION.md)

```bash
curl -sf http://localhost:3100/ready
curl -sf http://localhost:9090/-/healthy
curl -X POST http://localhost:8090/webhook/alert/checkout-redis-pool.json
```
