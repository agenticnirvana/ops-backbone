"""SRE demo scenarios — aligned with Runbooks/ seed runbooks for RAG + UI."""

from __future__ import annotations

SRE_SCENARIOS: list[dict] = [
    {
        "domain": "sre",
        "label": "Checkout Redis pool (capstone)",
        "runbook_id": "checkout-redis-pool",
        "summary": "Redis connection pool exhausted — checkout returning HTTP 500s.",
        "dependency": "Redis connection pool",
        "blast_radius": "/checkout endpoint · cart & payment flow · P1 revenue impact",
        "plan": [
            "Helm: set <code>REDIS_MAX_CONNECTIONS</code> 50 → 150",
            "Rolling restart <code>checkout-service</code> deployment",
            "Scale checkout replicas if traffic spike persists",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["redis", "connection-pool", "checkout-service"],
        "alert_name": "CheckoutHighErrorRate",
        "payload": {
            "domain": "sre",
            "service": "checkout-service",
            "severity": "P1",
            "error_summary": "HTTP 500 spike on /checkout",
            "log_snippet": (
                "2025-05-20T10:15:47Z ERROR checkout-service QueryTimeoutException: "
                "Timeout waiting for connection pool (Redis)\n"
                "2025-05-20T10:15:48Z WARN  checkout-service retry attempt 3/5 for /checkout\n"
                "2025-05-20T10:15:49Z ERROR checkout-service HTTP 500 /checkout upstream timeout"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Payment high CPU",
        "runbook_id": "payment-high-cpu",
        "summary": "Payment API CPU sustained above 90% — retry storm after deploy v2.4.1.",
        "dependency": "payment-api compute · card processor webhooks",
        "blast_radius": "/payments/charge · checkout completion blocked · P1 revenue",
        "plan": [
            "Rollback <code>payment-api</code> to previous Helm revision",
            "Enable circuit breaker on downstream processor calls",
            "Scale payment-api HPA if traffic-driven (max 10 replicas)",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["cpu", "retry-storm", "payment-api"],
        "alert_name": "PaymentHighCPU",
        "payload": {
            "domain": "sre",
            "service": "payment-api",
            "severity": "P1",
            "error_summary": "High CPU usage above 90%",
            "log_snippet": (
                "2025-05-20T11:02:11Z WARN  payment-api CPU 94% sustained 6m\n"
                "2025-05-20T11:02:12Z ERROR payment-api upstream timeout retry 4/5\n"
                "2025-05-20T11:02:13Z WARN  payment-api deploy v2.4.1 correlated with spike"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Auth error spike",
        "runbook_id": "auth-error-spike",
        "summary": "JWT validation failures causing elevated 5xx on login and token refresh.",
        "dependency": "Identity provider · JWT signing certificates",
        "blast_radius": "/oauth/token · session refresh · P2 login degradation",
        "plan": [
            "Verify IdP status and upstream latency",
            "Rotate JWT signing certs from Vault if expiry detected",
            "Enable cached session fallback if IdP outage confirmed",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["jwt", "auth-service", "identity"],
        "alert_name": "AuthErrorRateHigh",
        "payload": {
            "domain": "sre",
            "service": "auth-service",
            "severity": "P2",
            "error_summary": "5xx error rate spike on auth endpoints",
            "log_snippet": (
                "2025-05-20T09:44:01Z ERROR auth-service JWT validation failed: signature invalid\n"
                "2025-05-20T09:44:02Z WARN  auth-service token refresh failures +340/min\n"
                "2025-05-20T09:44:03Z ERROR auth-service HTTP 503 /oauth/token"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "DB pool exhausted",
        "runbook_id": "db-pool-exhausted",
        "summary": "Order service Hikari pool wait time exceeded — orders failing to persist.",
        "dependency": "PostgreSQL primary · order-service connection pool",
        "blast_radius": "/orders · fulfillment pipeline · P1 order loss risk",
        "plan": [
            "Identify and kill long-running queries (HITL approval required)",
            "Rolling restart <code>order-service</code> to reset pool",
            "Scale read replicas if read-heavy workload",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["postgres", "connection-pool", "order-service"],
        "alert_name": "OrderDBPoolExhausted",
        "payload": {
            "domain": "sre",
            "service": "order-service",
            "severity": "P1",
            "error_summary": "Database connection pool exhausted",
            "log_snippet": (
                "2025-05-20T12:18:22Z ERROR order-service HikariPool timeout waiting for connection\n"
                "2025-05-20T12:18:23Z WARN  order-service pool wait 2.4s exceeds threshold\n"
                "2025-05-20T12:18:24Z ERROR order-service failed to persist order id=ord-8821"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "API gateway latency",
        "runbook_id": "api-gateway-latency",
        "summary": "504 Gateway Timeout spike — upstream services slow across multiple routes.",
        "dependency": "nginx ingress · upstream service mesh",
        "blast_radius": "All public API routes · mobile app · P1 broad customer impact",
        "plan": [
            "Identify slowest upstream from distributed traces",
            "Increase upstream timeout for affected routes (HITL approval)",
            "Scale api-gateway replicas if CPU-bound",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["gateway", "latency", "504"],
        "alert_name": "GatewayLatencyP99High",
        "payload": {
            "domain": "sre",
            "service": "api-gateway",
            "severity": "P1",
            "error_summary": "504 Gateway Timeout rate above 2%",
            "log_snippet": (
                "2025-05-20T13:05:01Z ERROR api-gateway upstream timed out route=/checkout\n"
                "2025-05-20T13:05:02Z WARN  api-gateway p99 latency 6.2s threshold 5s\n"
                "2025-05-20T13:05:03Z ERROR api-gateway HTTP 504 /catalog/search"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Kafka consumer lag",
        "runbook_id": "kafka-consumer-lag",
        "summary": "Order events consumer lag > 100k — order status updates delayed.",
        "dependency": "Kafka · order-events-consumer group",
        "blast_radius": "Order status webhooks · shipping notifications · P1 SLA breach",
        "plan": [
            "Scale <code>order-events-consumer</code> deployment horizontally",
            "Skip poison message after manual review (HITL approval)",
            "Verify broker disk and under-replicated partitions",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["kafka", "consumer-lag", "events"],
        "alert_name": "KafkaConsumerLagCritical",
        "payload": {
            "domain": "sre",
            "service": "order-events-consumer",
            "severity": "P1",
            "error_summary": "Consumer lag > 100k messages on orders.created",
            "log_snippet": (
                "2025-05-20T14:22:10Z WARN  order-events-consumer lag 142891 messages\n"
                "2025-05-20T14:22:11Z ERROR order-events-consumer failed to commit offset\n"
                "2025-05-20T14:22:12Z WARN  order-events-consumer rebalance storm detected"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Search service degraded",
        "runbook_id": "search-service-degraded",
        "summary": "OpenSearch cluster yellow — product search timeouts and empty results.",
        "dependency": "OpenSearch cluster · search-service index cache",
        "blast_radius": "/search · catalog browse · P2 discovery degradation",
        "plan": [
            "Reroute unassigned shards or add data nodes",
            "Enable query timeout cap with partial results banner",
            "Roll back recent index mapping change if correlated",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["opensearch", "search", "latency"],
        "alert_name": "SearchTimeoutRateHigh",
        "payload": {
            "domain": "sre",
            "service": "search-service",
            "severity": "P2",
            "error_summary": "Search timeout rate above 10%",
            "log_snippet": (
                "2025-05-20T15:10:44Z WARN  search-service OpenSearch cluster status YELLOW\n"
                "2025-05-20T15:10:45Z ERROR search-service query timeout after 800ms\n"
                "2025-05-20T15:10:46Z WARN  search-service empty results rate +18%"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Inventory sync failure",
        "runbook_id": "inventory-sync-failure",
        "summary": "ERP sync job failed — stock mismatch and oversell risk on hot SKUs.",
        "dependency": "ERP API · inventory-service sync worker",
        "blast_radius": "Product availability · checkout validation · P1 oversell risk",
        "plan": [
            "Enable oversell protection mode (<code>INVENTORY_HARD_STOP=true</code>)",
            "Trigger manual full ERP sync (HITL approval during peak)",
            "Pause marketing campaigns for affected SKUs",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["inventory", "erp", "sync"],
        "alert_name": "InventorySyncFailed",
        "payload": {
            "domain": "sre",
            "service": "inventory-service",
            "severity": "P1",
            "error_summary": "ERP inventory sync job failed — stock mismatch",
            "log_snippet": (
                "2025-05-20T16:33:01Z ERROR inventory-service ERP sync failed: 401 Unauthorized\n"
                "2025-05-20T16:33:02Z WARN  inventory-service SKU-4412 warehouse=-3 vs ERP=12\n"
                "2025-05-20T16:33:03Z ERROR inventory-service oversell guard triggered checkout block"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Notification delivery backlog",
        "runbook_id": "notification-delivery-backlog",
        "summary": "Email/SMS queue depth > 50k — OTP and order confirmations delayed.",
        "dependency": "SendGrid · Twilio · notification workers",
        "blast_radius": "Transactional email/SMS · OTP login · P2 comms SLA",
        "plan": [
            "Scale notification worker deployment",
            "Throttle non-critical marketing sends",
            "Fail over to secondary email provider if rate-limited",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["email", "sms", "queue"],
        "alert_name": "NotificationQueueDepthHigh",
        "payload": {
            "domain": "sre",
            "service": "notification-service",
            "severity": "P2",
            "error_summary": "Notification queue depth > 50k messages",
            "log_snippet": (
                "2025-05-20T17:01:18Z WARN  notification-service queue depth 52841\n"
                "2025-05-20T17:01:19Z ERROR notification-service SendGrid 429 rate limit\n"
                "2025-05-20T17:01:20Z WARN  notification-service OTP delivery p95 8m"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Kubernetes OOM restart",
        "runbook_id": "kubernetes-oom-restart",
        "summary": "Catalog service pods OOMKilled — restart loop after memory regression.",
        "dependency": "catalog-service JVM heap · K8s memory limits",
        "blast_radius": "/catalog · product metadata API · P2 browse degradation",
        "plan": [
            "Increase memory limit 512Mi → 1Gi (HITL approval)",
            "Rolling restart catalog-service after limit change",
            "Roll back deploy if memory regression from last release",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["kubernetes", "oom", "catalog-service"],
        "alert_name": "CatalogPodOOMKilled",
        "payload": {
            "domain": "sre",
            "service": "catalog-service",
            "severity": "P2",
            "error_summary": "Pods OOMKilled — restart loop on catalog-service",
            "log_snippet": (
                "2025-05-20T18:44:55Z ERROR catalog-service pod oom-killed exit 137\n"
                "2025-05-20T18:44:56Z WARN  catalog-service memory 512Mi limit exceeded\n"
                "2025-05-20T18:44:57Z ERROR catalog-service CrashLoopBackOff replica 2/3"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "TLS certificate expiry",
        "runbook_id": "tls-certificate-expiry",
        "summary": "Production TLS cert expires in < 72h — cert-manager renewal failing.",
        "dependency": "cert-manager · Let's Encrypt · edge ingress",
        "blast_radius": "All customer-facing HTTPS · mobile app · P1 trust outage risk",
        "plan": [
            "Force cert-manager certificate renewal annotation",
            "Upload renewed cert from Vault if ACME failing (HITL approval)",
            "Route via backup ingress with valid cert if imminent expiry",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["tls", "cert-manager", "ingress"],
        "alert_name": "TLSCertExpiringSoon",
        "payload": {
            "domain": "sre",
            "service": "edge-ingress",
            "severity": "P1",
            "error_summary": "TLS certificate expires in 48 hours — renewal failed",
            "log_snippet": (
                "2025-05-20T19:12:01Z ERROR cert-manager Certificate shop.example.com NotReady\n"
                "2025-05-20T19:12:02Z WARN  edge-ingress ACME challenge DNS-01 failed\n"
                "2025-05-20T19:12:03Z ERROR edge-ingress cert NotAfter 2025-05-22T00:00:00Z"
            ),
        },
    },
    {
        "domain": "sre",
        "label": "Deployment canary failure",
        "runbook_id": "deployment-canary-failure",
        "summary": "Recommendation service canary analysis failed — error rate above stable baseline.",
        "dependency": "Argo Rollouts · recommendation-service model v3",
        "blast_radius": "/recommendations · homepage personalization · P1 conversion impact",
        "plan": [
            "Abort Argo Rollout and rollback to stable revision",
            "Disable feature flag from canary release",
            "Hold further deploys until postmortem (HITL to retry canary)",
        ],
        "runbook_sections": ["Diagnosis", "Remediation", "Verification", "Escalation"],
        "tags": ["canary", "argo-rollouts", "ml-serving"],
        "alert_name": "CanaryAnalysisFailed",
        "payload": {
            "domain": "sre",
            "service": "recommendation-service",
            "severity": "P1",
            "error_summary": "Canary error rate 2.1% above stable baseline",
            "log_snippet": (
                "2025-05-20T20:05:33Z ERROR recommendation-service canary analysis failed\n"
                "2025-05-20T20:05:34Z WARN  recommendation-service 5xx rate canary 3.8% vs stable 1.2%\n"
                "2025-05-20T20:05:35Z INFO  argo-rollouts aborting rollout recommendation-service"
            ),
        },
    },
]


def list_sre_scenarios() -> list[dict]:
    return SRE_SCENARIOS
