# Deployment canary failure

**Service:** recommendation-service  
**Severity:** P1  
**Triggers:** canary error rate > baseline + 2%, Argo Rollouts degraded, automated rollback triggered

## Diagnosis

1. Check Argo Rollouts status — canary weight, analysis run result
2. Compare error rate canary vs stable (`http_5xx_rate` by rollout pod-template-hash)
3. Review deploy diff — config, feature flags, dependency version bumps
4. Inspect canary pod logs for startup failures or missing secrets
5. Verify analysis queries (success rate, latency) in Prometheus

## Remediation

- **Automatic:** Argo Rollouts abort and rollback if analysis fails (verify rollback completed)
- Manual: `kubectl argo rollouts abort recommendation-service` if stuck
- Disable feature flag introduced in canary if root cause identified
- Hold further deploys to service until postmortem action items addressed
- **Requires HITL approval** to retry canary after rollback

## Verification

- Stable revision serving 100% traffic
- Error rate returned to pre-deploy baseline for 15 minutes
- Rollout status Healthy with no in-progress canary

## Escalation

Notify release manager and page ML platform if model-serving regression suspected.
