"""OPA policy gate — authorize destructive remediation actions."""

from __future__ import annotations

import os

import httpx


def check_action_allowed(*, service: str, recommendation: str, severity: str) -> tuple[bool, str]:
    """Return (allowed, reason). Uses OpenFGA when OPENFGA_URL is set, else OPA."""
    from observability.trace_context import trace_tool

    backend = "openfga" if os.getenv("OPENFGA_URL") else "opa"
    with trace_tool(
        "🔧 Tool · OpenFGA Check" if backend == "openfga" else "🔧 Tool · OPA Policy Check",
        input={"service": service, "severity": severity, "recommendation": recommendation[:300]},
        metadata={"integration": backend},
    ) as span:
        allowed, reason = _check_action_allowed_impl(service=service, recommendation=recommendation, severity=severity)
        if span:
            span.end(output={"allowed": allowed, "reason": reason})
        from observability.trace_context import emit_event

        emit_event(
            "⚖️ Event · Policy allow" if allowed else "⚖️ Event · Policy deny",
            input={"service": service, "severity": severity},
            output={"allowed": allowed, "reason": reason},
            metadata={"phase": "4-guardrails", "integration": backend},
            level="DEFAULT" if allowed else "WARNING",
        )
        return allowed, reason


def _local_allow(*, recommendation: str, severity: str) -> tuple[bool, str]:
    text = recommendation.lower()
    destructive = any(k in text for k in ("restart", "rollback", "kill", "delete", "scale-down"))
    if not destructive:
        return True, "policy_allow"
    if severity == "P1":
        return True, "policy_allow"
    return False, "policy_deny"


def _openfga_authorized() -> bool:
    base = os.getenv("OPENFGA_URL", "").rstrip("/")
    if not base:
        return True
    with httpx.Client(timeout=5.0) as client:
        stores = client.get(f"{base}/stores").json().get("stores") or []
        if not stores:
            return False
        store_id = os.getenv("OPENFGA_STORE_ID") or stores[0].get("id")
        r = client.post(
            f"{base}/stores/{store_id}/check",
            json={
                "tuple_key": {
                    "user": "user:ops-agent",
                    "relation": "execute",
                    "object": "action:remediate",
                }
            },
        )
        r.raise_for_status()
        return bool(r.json().get("allowed"))


def _presidio_findings(text: str) -> list[dict]:
    url = os.getenv("PRESIDIO_URL", "").rstrip("/")
    if not url or not text:
        return []
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(f"{url}/analyze", json={"text": text, "language": "en"})
            r.raise_for_status()
            return r.json() if isinstance(r.json(), list) else []
    except Exception:
        return []


def _check_action_allowed_impl(*, service: str, recommendation: str, severity: str) -> tuple[bool, str]:
    if os.getenv("OPENFGA_URL", "").rstrip("/"):
        try:
            if not _openfga_authorized():
                return False, "openfga_deny"
            allowed, reason = _local_allow(recommendation=recommendation, severity=severity)
            findings = _presidio_findings(recommendation)
            if findings and os.getenv("PRESIDIO_BLOCK", "false").lower() == "true":
                return False, "presidio_pii"
            return allowed, ("openfga_allow" if allowed else reason)
        except Exception as exc:
            if os.getenv("OPA_FAIL_OPEN", "false").lower() == "true":
                return True, f"openfga_error_fail_open:{exc}"
            return False, f"openfga_error:{exc}"

    opa_url = os.getenv("OPA_URL", "").rstrip("/")
    if not opa_url:
        return True, "opa_disabled"

    payload = {
        "input": {
            "service": service,
            "severity": severity,
            "recommendation": recommendation,
        }
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{opa_url}/v1/data/agentops/allow", json=payload)
            response.raise_for_status()
            data = response.json()
            allowed = bool(data.get("result", False))
            if allowed:
                return True, "policy_allow"
            return False, "policy_deny"
    except Exception as exc:
        # Fail closed in production stacks; operators can set OPA_FAIL_OPEN=true for dev.
        if os.getenv("OPA_FAIL_OPEN", "false").lower() == "true":
            return True, f"opa_error_fail_open:{exc}"
        return False, f"opa_error:{exc}"
