"""OPA policy evaluation for MCP — HTTP only, no PostgreSQL/SQLAlchemy."""

from __future__ import annotations

import os
from typing import Any

import httpx

DESTRUCTIVE_KEYWORDS = ("restart", "rollback", "kill", "delete", "scale-down")

POLICY_RULES = [
    {"id": "allow_non_destructive", "label": "Non-destructive recommendation", "effect": "allow"},
    {"id": "allow_p1_destructive", "label": "Destructive action + P1 severity", "effect": "allow"},
    {"id": "deny_destructive_not_p1", "label": "Destructive action on P2/P3", "effect": "deny"},
    {"id": "deny_default", "label": "Default deny (no matching allow rule)", "effect": "deny"},
]


def is_destructive(recommendation: str) -> bool:
    text = recommendation.lower()
    return any(keyword in text for keyword in DESTRUCTIVE_KEYWORDS)


def matched_rule_for(*, allowed: bool, destructive: bool, severity: str) -> str:
    if allowed and not destructive:
        return "allow_non_destructive"
    if allowed and destructive and severity == "P1":
        return "allow_p1_destructive"
    if not allowed and destructive:
        return "deny_destructive_not_p1"
    return "deny_default"


def evaluate_with_opa(*, service: str, recommendation: str, severity: str) -> tuple[bool, str]:
    if os.getenv("OPENFGA_URL", "").rstrip("/"):
        from agent.tools.policy_check import check_action_allowed

        return check_action_allowed(service=service, recommendation=recommendation, severity=severity)
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
            allowed = bool(response.json().get("result", False))
            return (True, "policy_allow") if allowed else (False, "policy_deny")
    except Exception as exc:
        if os.getenv("OPA_FAIL_OPEN", "false").lower() == "true":
            return True, f"opa_error_fail_open:{exc}"
        return False, f"opa_error:{exc}"


def build_evaluation_result(
    *,
    service: str,
    recommendation: str,
    severity: str,
    allowed: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    destructive = is_destructive(recommendation)
    if allowed is None or reason is None:
        allowed, reason = evaluate_with_opa(
            service=service,
            recommendation=recommendation,
            severity=severity,
        )
    matched_rule = matched_rule_for(allowed=allowed, destructive=destructive, severity=severity)
    return {
        "allowed": allowed,
        "reason": reason,
        "destructive": destructive,
        "severity": severity,
        "service": service,
        "matched_rule": matched_rule,
        "opa_url": os.getenv("OPA_URL", "http://opa:8181"),
        "input": {
            "service": service,
            "severity": severity,
            "recommendation": recommendation,
        },
    }
