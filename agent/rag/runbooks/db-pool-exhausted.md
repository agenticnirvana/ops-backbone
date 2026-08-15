# Database connection pool exhausted

**Service:** order-service  
**Severity:** P1  
**Triggers:** pool wait time > 2s, `order_api_latency_p99` spike, Hikari pool timeout errors

## Diagnosis

1. Query Postgres for long-running queries (`pg_stat_activity`, duration > 30s)
2. Review recent traffic spike or batch jobs hitting order-service
3. Inspect application logs for connection leak warnings
4. Check read replica lag — stale reads can cause retry loops
5. Confirm no migration job holding locks on orders table

## Remediation

- Kill long-running queries blocking pool — **requires HITL approval** (include query PID)
- Temporarily scale read replicas if read-heavy workload
- Restart order-service pods to reset pool — **requires HITL approval**
- Increase pool size from 20 to 40 if sustained load (config change needs approval)

## Verification

- Pool wait time below 200ms for 10 minutes
- Order placement success rate restored above 99%
- No new pool timeout errors in Loki for 15 minutes

## Escalation

Page DBA on-call if primary DB CPU > 85% or replication lag > 30 seconds.
