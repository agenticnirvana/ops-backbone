# Payment service high CPU

**Service:** payment-api  
**Severity:** P1  
**Triggers:** CPU > 90% for 5 min, payment latency SLO breach, retry storm in logs

## Diagnosis

1. Check recent deploys to payment-api in last 30 minutes
2. Query error rate alongside CPU — retry storms often correlate with upstream 503s
3. Inspect connection pool metrics (`payment_db_pool_active`, `payment_db_pool_wait`)
4. Review Prometheus for traffic spike vs baseline (`payment_requests_total`)
5. Check card processor webhook backlog and timeout counts

## Remediation

- If bad deploy: rollback to previous version (`kubectl rollout undo deployment/payment-api`)
- If retry storm: enable circuit breaker on downstream calls (`PAYMENT_CB_ENABLED=true`)
- If connection leak: rolling restart payment-api pods — **requires HITL approval**
- Scale horizontally if sustained traffic increase (HPA max 10 replicas)

## Verification

- CPU below 70% for 15 minutes on all payment-api pods
- Payment success rate above 99.5% for 10 minutes
- No growing retry queue in processor dashboard

## Escalation

Page on-call platform lead if not resolved in 15 minutes or if payment success rate drops below 95%.
