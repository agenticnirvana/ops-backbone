# Sample data — SRE ops fixtures (Design 1)

Production-style alert payloads, logs, and metrics for the **SRE capstone** path.

| Path | Role |
|------|------|
| `alerts/` | Alertmanager / webhook fixtures |
| `logs/` | Promtail → Loki JSONL |
| `metrics/services.json` | Prometheus demo gauges |

## SRE alerts

| File | Service | Use for |
|------|---------|---------|
| `payment-high-cpu.json` | payment-api | P1 CPU demo |
| `auth-error-spike.json` | auth-service | P2, no HITL |
| `db-pool-exhausted.json` | order-service | DB runbook RAG |
| `checkout-redis-pool.json` | checkout-service | **Capstone** — Redis pool |

## Quick invoke

```bash
cd ../deploy && ./deploy.sh up
curl -X POST http://localhost:8090/webhook/alert/checkout-redis-pool.json
```

Or direct agent:

```bash
curl -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d @alerts/checkout-redis-pool.json
```
