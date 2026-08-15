# Search service degraded

**Service:** search-service  
**Severity:** P2  
**Triggers:** search timeout rate > 10%, empty result rate spike, OpenSearch cluster yellow/red

## Diagnosis

1. Check OpenSearch cluster health (`/_cluster/health`) — shards unassigned?
2. Review query latency percentiles in Prometheus
3. Inspect recent index rebuild or mapping change jobs
4. Compare cache hit rate — cold cache after deploy causes latency spikes
5. Check for expensive wildcard queries in slow query log

## Remediation

- If cluster yellow: reroute unassigned shards or add data nodes
- If hot shard: increase replicas for affected index
- Enable query timeout cap (500ms) and return partial results with banner
- Roll back recent index mapping change if correlated with incident start
- **Requires HITL approval** for cluster topology or index setting changes

## Verification

- Search p95 latency below 300ms for 15 minutes
- Cluster status green with all primary shards active
- Product search smoke test returns expected results for top 20 queries

## Escalation

Page search platform team if cluster red or data loss suspected.
