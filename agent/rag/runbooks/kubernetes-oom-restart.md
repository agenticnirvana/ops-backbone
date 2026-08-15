# Kubernetes OOM pod restarts

**Service:** catalog-service  
**Severity:** P2  
**Triggers:** OOMKilled events, pod restart loop, JVM heap exhaustion in logs

## Diagnosis

1. Check `kube_pod_container_status_restarts_total` for catalog-service
2. Review memory limits vs actual usage (`container_memory_working_set_bytes`)
3. Inspect heap dump or GC logs if JVM service
4. Correlate with traffic spike or cache warm-up after deploy
5. Verify no memory leak pattern — restarts every N minutes on same pod

## Remediation

- Increase memory limit from 512Mi to 1Gi — **requires HITL approval** for prod change
- Rolling restart affected deployment after limit change
- Enable JVM heap dump on OOM for post-incident analysis (staging first)
- Roll back deploy if memory regression introduced in last release

## Verification

- Zero OOMKilled events for 2 hours
- Pod restart count stable
- Memory usage below 80% of new limit under peak load

## Escalation

Page application team if OOM persists after limit increase — likely code-level leak.
