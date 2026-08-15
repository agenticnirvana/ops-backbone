# Notification delivery backlog

**Service:** notification-service  
**Severity:** P2  
**Triggers:** email/SMS queue depth > 50k, delivery latency > 10 min, provider 429 errors

## Diagnosis

1. Check notification queue depth metric (`notification_queue_pending`)
2. Review SendGrid/Twilio provider status and rate-limit headers
3. Inspect failed delivery webhooks and bounce rate spike
4. Identify bulk campaign vs transactional traffic mix
5. Verify worker pod count matches HPA configuration

## Remediation

- Scale notification workers horizontally
- Throttle non-critical marketing sends temporarily
- Switch to secondary email provider if primary is rate-limiting
- Replay dead-letter queue after fixing root cause — **requires HITL approval** for mass replay
- Purge duplicate enqueue from buggy deploy if identified

## Verification

- Queue depth below 500 for 30 minutes
- Transactional OTP and order confirmation delivery under 60s
- Provider error rate below 0.5%

## Escalation

Page customer comms lead if order/shipping notifications delayed beyond 30 minutes.
