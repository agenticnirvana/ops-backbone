# Redis connection pool exhaustion

**Service:** checkout-service  
**Severity:** P1  
**Triggers:** HTTP 5xx on /checkout, Redis pool timeout in logs, `checkout_latency_p99` > 3s

## Diagnosis

1. Check Redis active connections vs `REDIS_MAX_CONNECTIONS` in Grafana (`redis_connected_clients`)
2. Confirm Postgres CPU is normal — rule out DB as root cause
3. Review traffic spike or deploy in the last 30 minutes (Prometheus `http_requests_total`)
4. Inspect checkout-service logs in Loki for `Timeout waiting for connection pool`
5. Verify no stuck transactions holding connections open

## Remediation

- Increase `REDIS_MAX_CONNECTIONS` from 50 to 150 in Helm values (`checkout-service`)
- Rolling restart checkout-service deployment
- Scale checkout-service horizontally if traffic spike is sustained
- **Requires HITL approval** for production config change and pod restart

## Verification

- Poll `http_5xx_rate{service="checkout-service"}` for 2 minutes until below 0.1%
- Confirm Redis active connections below new max threshold
- Run synthetic checkout probe from staging smoke test
- Log resolved incident in ticketing system

## Escalation

Page platform on-call if pool exhaustion recurs within 1 hour after fix.
