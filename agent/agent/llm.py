"""LLM client — OpenAI-compatible API with mock fallback for CI."""

from __future__ import annotations

import json
import os


def call_llm(system: str, user: str, mock: bool | None = None) -> str:
    from observability.trace_context import infer_llm_trace_name, trace_llm_generation

    trace_name = f"💬 {infer_llm_trace_name(system)}"

    def _invoke() -> str:
        use_mock = mock if mock is not None else os.getenv("MOCK_LLM", "false").lower() == "true"
        if use_mock:
            return _mock_response(system, user)

        if os.getenv("LLM_PROVIDER", "").lower() == "bedrock":
            try:
                return _bedrock_call(system, user)
            except Exception as exc:
                return _mock_response(system, user, error=str(exc))

        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or ("local" if os.getenv("OPENAI_BASE_URL") else None)
        )
        if not api_key:
            return _mock_response(system, user)

        try:
            from openai import OpenAI

            base_url = os.getenv("OPENAI_BASE_URL")
            client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            return _mock_response(system, user, error=str(exc))

    return trace_llm_generation(trace_name, system, user, _invoke)


def _bedrock_call(system: str, user: str) -> str:
    import boto3

    model_id = os.getenv("LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    client = boto3.client("bedrock-runtime", region_name=region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "temperature": 0.2,
    }
    resp = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    content = payload.get("content") or []
    if content and isinstance(content[0], dict):
        return content[0].get("text", "")
    return str(payload)


def _mock_response(system: str, user: str, error: str | None = None) -> str:
    sys_lower = system.lower()
    if "write a new sre runbook" in sys_lower or "runbook in github-flavored" in sys_lower:
        try:
            payload = json.loads(user)
        except json.JSONDecodeError:
            payload = {}
        service = payload.get("service") or "unknown-service"
        summary = payload.get("error_summary") or "unmatched alert"
        title = f"{service} — {summary}"
        markdown = (
            f"# {title}\n\n"
            f"**Service:** {service}  \n"
            f"**Severity:** {payload.get('severity') or 'P2'}  \n"
            f"**Triggers:** {summary}\n\n"
            "## Diagnosis\n\n1. Capture a precise log line\n2. Check error rate and last deploy\n\n"
            "## Remediation\n\nInvestigate with HITL approval before production change.\n\n"
            "## Verification\n\n- Error rate returns below threshold\n\n"
            "## Escalation\n\nPage the service owner if it recurs within 1 hour.\n"
        )
        return json.dumps({"title": title, "markdown": markdown})
    if "llm-as-judge" in sys_lower or "llm as judge" in sys_lower:
        return json.dumps(
            {
                "score": 0.9,
                "reason": "Recommendation cites the expected runbook and grounded remediation steps.",
            }
        )
    if "classify" in sys_lower:
        requires = "P1" in user or "P0" in user
        return json.dumps({"classification": "infra_cpu", "requires_hitl": requires})
    if "recommend" in sys_lower or "remediation" in sys_lower:
        if "no grounded runbook" in sys_lower or "runbook_gap" in sys_lower:
            return json.dumps(
                {
                    "recommendation": (
                        "No matching runbook. Capture a precise log signature, check error rate and last deploy, "
                        "open a ticket, then draft a new runbook and embed it."
                    ),
                    "runbook_id": "none",
                    "citations": [],
                    "runbook_gap": True,
                }
            )
        service = ""
        try:
            payload = json.loads(user)
            service = payload.get("alert", {}).get("service", "")
        except json.JSONDecodeError:
            pass
        runbook_id = "payment-high-cpu"
        recommendation = "Rollback recent deploy and scale horizontally. Restart requires approval."
        if service == "auth-service":
            runbook_id = "auth-error-spike"
            recommendation = "Check IdP status and rotate certificate if JWT validation fails."
        elif service == "order-service":
            runbook_id = "db-pool-exhausted"
            recommendation = "Kill long-running queries and scale read replicas. Restart pool requires approval."
        elif service == "checkout-service":
            runbook_id = "checkout-redis-pool"
            recommendation = "Increase REDIS_MAX_CONNECTIONS from 50 to 150 in Helm values. Rolling restart requires approval."
        elif service == "api-gateway":
            runbook_id = "api-gateway-latency"
            recommendation = "Identify slow upstream from traces and adjust timeout. Gateway config change requires approval."
        elif service == "order-events-consumer":
            runbook_id = "kafka-consumer-lag"
            recommendation = "Scale consumer deployment and skip poison message after review. Requires approval."
        elif service == "search-service":
            runbook_id = "search-service-degraded"
            recommendation = "Reroute unassigned shards and enable query timeout cap. Index changes require approval."
        elif service == "inventory-service":
            runbook_id = "inventory-sync-failure"
            recommendation = "Enable oversell protection and trigger manual ERP sync. Requires approval during peak."
        elif service == "notification-service":
            runbook_id = "notification-delivery-backlog"
            recommendation = "Scale notification workers and throttle marketing sends."
        elif service == "catalog-service":
            runbook_id = "kubernetes-oom-restart"
            recommendation = "Increase memory limit to 1Gi and rolling restart. Requires approval."
        elif service == "edge-ingress":
            runbook_id = "tls-certificate-expiry"
            recommendation = "Force cert-manager renewal or upload cert from Vault. Requires approval."
        elif service == "recommendation-service":
            runbook_id = "deployment-canary-failure"
            recommendation = "Abort Argo Rollout and rollback to stable revision. Retry canary requires approval."
        elif service == "onboarding-queue":
            runbook_id = "onboarding-sla-breach"
            recommendation = "Escalate IT asset assignment and offer loaner device. Expedited procurement requires HRBP approval."
        elif service == "compensation-queue":
            runbook_id = "compensation-review"
            recommendation = "Route off-cycle exception to HRBP and Finance for dual HITL approval before updating Workday."
        elif service == "employee-self-service":
            runbook_id = "expense-reimbursement-policy"
            recommendation = "Home office furniture cap is $500/year. Chair over $300 needs pre-approval; $650 exceeds cap."
        elif service == "security-compliance":
            runbook_id = "data-classification-handling"
            recommendation = "Deny PII export to personal laptop. Open security review and require approved DLP pipeline."
        return json.dumps(
            {
                "recommendation": recommendation,
                "runbook_id": runbook_id,
                "citations": [f"{runbook_id}.md"],
            }
        )
    prefix = f"[mock{' error=' + error if error else ''}] "
    return prefix + "Proceed with runbook remediation steps."
