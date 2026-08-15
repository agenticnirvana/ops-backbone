"""Ticket creation — mock locally, HTTP webhook in deploy stack, Jira/ServiceNow in prod."""

from __future__ import annotations

import os
import uuid

import httpx

TICKET_WEBHOOK_URL = os.getenv("TICKET_WEBHOOK_URL", "").strip()


def create_ticket(
    service: str,
    severity: str,
    recommendation: str,
    runbook_id: str,
    *,
    approved_by: str | None = None,
) -> dict:
    """Create ops ticket via webhook if configured, else return mock payload."""
    from observability.trace_context import trace_tool

    payload = {
        "service": service,
        "severity": severity,
        "action": "remediation",
        "recommendation": recommendation,
        "runbook_id": runbook_id,
        "approved_by": approved_by or os.getenv("HITL_APPROVER", "agent"),
    }
    with trace_tool(
        "🔧 Tool · Create Ticket",
        input=payload,
        metadata={"integration": "ticket_webhook", "webhook": bool(TICKET_WEBHOOK_URL)},
    ) as span:
        result = _create_ticket_impl(payload)
        if span:
            span.end(output={"ticket_id": result.get("ticket_id"), "status": result.get("status")})
        return result


def _create_ticket_impl(payload: dict) -> dict:

    if TICKET_WEBHOOK_URL:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(TICKET_WEBHOOK_URL, json=payload)
                r.raise_for_status()
                data = r.json()
                if "ticket_id" not in data and "id" in data:
                    data["ticket_id"] = data["id"]
                return data
        except Exception as exc:
            return {
                "ticket_id": f"OPS-FAIL-{uuid.uuid4().hex[:6].upper()}",
                "status": "error",
                "message": str(exc),
                **payload,
            }

    ticket_id = f"OPS-{uuid.uuid4().hex[:8].upper()}"
    return {
        "ticket_id": ticket_id,
        "service": payload["service"],
        "severity": payload["severity"],
        "status": "open",
        "summary": str(payload.get("recommendation") or "")[:120],
        "runbook_id": payload["runbook_id"],
        "url": f"https://ops.example.com/tickets/{ticket_id}",
    }
