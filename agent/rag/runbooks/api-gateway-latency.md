# API gateway latency spike

**Service:** api-gateway  
**Severity:** P1  
**Triggers:** 504 Gateway Timeout rate > 2%, `gateway_latency_p99` > 5s, upstream timeout errors

## Diagnosis

1. Check ingress/nginx error logs for upstream timeout patterns
2. Identify slowest upstream service from distributed trace (Langfuse / OTel)
3. Review recent rate-limit or WAF rule changes
4. Compare latency by route — isolate `/checkout` vs `/catalog` vs `/search`
5. Verify gateway pod CPU and connection count are within limits

## Remediation

- Increase upstream timeout for affected routes if backend is legitimately slow (temporary)
- Enable request hedging for idempotent GET routes if configured
- Scale api-gateway replicas if CPU-bound
- If single upstream is root cause: route traffic to healthy AZ or enable degraded mode banner
- **Requires HITL approval** for timeout or routing config changes in production

## Verification

- `gateway_latency_p99` below 1s for 10 minutes
- 504 rate below 0.1% on all critical routes
- Synthetic probes green for checkout, search, and auth paths

## Escalation

Page platform SRE if multiple upstreams degraded simultaneously (possible network partition).
