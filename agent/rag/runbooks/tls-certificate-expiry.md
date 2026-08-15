# TLS certificate expiry imminent

**Service:** edge-ingress  
**Severity:** P1  
**Triggers:** cert expires in < 72h, browser SSL warnings, cert-manager Certificate NotReady

## Diagnosis

1. Check cert-manager Certificate resource status (`kubectl describe certificate`)
2. Verify ACME/Let's Encrypt order failures in cert-manager logs
3. Confirm DNS challenge records if using DNS-01 solver
4. List all ingress TLS secrets nearing expiry in monitoring dashboard
5. Review if recent DNS or Cloudflare change broke validation

## Remediation

- Force cert-manager renewal: `kubectl annotate certificate <name> cert-manager.io/issue-temporary-certificate="true"`
- If ACME failing: manually upload renewed cert from Vault — **requires HITL approval**
- Extend cert validity via approved CA process if automated renewal blocked
- Temporarily route traffic through backup ingress with valid cert if available

## Verification

- Certificate NotAfter date > 30 days from now
- SSL Labs probe shows valid chain for all customer-facing domains
- No cert expiry alerts firing in Prometheus

## Escalation

Page security/platform immediately if cert already expired in production.
