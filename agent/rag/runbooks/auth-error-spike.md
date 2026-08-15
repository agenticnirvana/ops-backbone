# Auth service error spike

**Service:** auth-service  
**Severity:** P2  
**Triggers:** 5xx rate > 5%, JWT validation failures in logs, login success rate drop

## Diagnosis

1. Check identity provider status page and upstream latency
2. Query Loki for `JWT validation failed` and `token expired` error patterns
3. Verify certificate expiry on JWT signing keys in Vault (`auth_jwt_cert_expiry_days`)
4. Compare error rate by pod — isolate bad replica vs fleet-wide issue
5. Review recent config deploy to auth-service in last 2 hours

## Remediation

- If IdP outage: enable cached session fallback mode (`AUTH_SESSION_CACHE=true`)
- If cert expiry: rotate signing certs from Vault and rolling restart auth pods
- If bad config: revert last Helm release (`helm rollback auth-service`)
- If credential attack suspected: enable stricter rate limits — notify security first

## Verification

- Confirm `http_5xx_rate{service="auth-service"}` below 1% for 10 minutes
- Validate login flow via synthetic probe (`/oauth/token`)
- Check no new cert expiry alerts in next 24h window

## Escalation

Notify security team if brute-force or credential stuffing patterns detected in WAF logs.
