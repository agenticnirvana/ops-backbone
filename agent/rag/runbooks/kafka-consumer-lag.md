# Kafka consumer lag critical

**Service:** order-events-consumer  
**Severity:** P1  
**Triggers:** consumer lag > 100k messages, order status updates delayed > 5 min

## Diagnosis

1. Check `kafka_consumer_lag` by consumer group in Grafana
2. Identify affected topics (`orders.created`, `orders.shipped`, `inventory.updated`)
3. Review consumer pod restarts and OOM events in last hour
4. Inspect for poison messages causing repeated processing failures
5. Verify broker disk usage and under-replicated partitions

## Remediation

- Scale consumer deployment horizontally (increase partition consumers)
- Pause and skip poison message after manual review — **requires HITL approval**
- Increase consumer `max.poll.records` temporarily if processing is CPU-bound
- If broker issue: fail over to standby cluster per platform runbook

## Verification

- Consumer lag below 1k messages for 15 minutes
- Order status webhook delivery within 30s SLA
- No consumer rebalance storm in logs

## Escalation

Page data platform on-call if lag grows after scale-out or if broker disk > 85%.
