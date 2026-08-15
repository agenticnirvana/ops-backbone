# Checkout Redis Pool Triage

Use this skill when an alert mentions **checkout**, **Redis**, or **connection pool** exhaustion — before calling live observability tools.

## When to use (Skill vs MCP)

| Use this **skill** | Use **MCP tool** instead |
|--------------------|--------------------------|
| Quick heuristic on fixture/sample metrics | Live Prometheus `get_metrics` |
| Teaching runbook recall pattern | Production incident with real data |
| Offline eval / golden-alert checks | Agent must act on current cluster state |

## Procedure

1. Run `check_redis_pool.py` with the service name.
2. If `redis_pool_exhausted` is true, retrieve runbook **checkout-redis-pool**.
3. Escalate to P1 if checkout error rate is elevated.
4. Do **not** restart Redis without HITL on P1 destructive actions.

## Capstone mapping

Design 1 capstone alert `checkout-redis-pool.json` → this skill + MCP `retrieve_runbooks` + `query_logs`.
