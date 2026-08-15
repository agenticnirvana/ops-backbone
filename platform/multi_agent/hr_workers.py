"""HR specialist workers — corporate multi-agent pipeline (dummy HRIS fixtures + policy RAG)."""

from __future__ import annotations

import json

from agent.llm import call_llm
from agent.tools.fixture_events import query_fixture_events
from agent.tools.runbook_rag import format_runbook_context, retrieve_runbooks
from agent.tools.ticket_create import create_ticket

SENSITIVE_HR_KEYWORDS = ("terminate", "off-cycle", "exception", "loaner", "expedited procurement", "above band")


def case_triage_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    system = (
        "Classify the HR case. Return JSON: classification (string), requires_hitl (bool). "
        "Examples: onboarding_sla, comp_exception, leave_policy."
    )
    raw = call_llm(system, json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        data = {
            "classification": "hr_case",
            "requires_hitl": alert.get("severity") in ("P1", "P0"),
        }
    trace = state.get("worker_trace", []) + ["case_triage_worker"]
    return {
        "classification": data.get("classification", "hr_case"),
        "requires_hitl": bool(data.get("requires_hitl")) or alert.get("severity") in ("P1", "P0"),
        "worker_trace": trace,
    }


def policy_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    service = alert.get("service", "")
    query = f"{service} {alert.get('error_summary', '')} {alert.get('log_snippet', '')}"
    chunks = retrieve_runbooks(query, service=service, domain="hr", top_k=3)
    trace = state.get("worker_trace", []) + ["policy_worker"]
    return {
        "runbook_chunks": chunks,
        "runbook_context": format_runbook_context(chunks),
        "worker_trace": trace,
    }


def records_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    events = query_fixture_events("hr", alert.get("service", ""), alert.get("error_summary", ""))
    trace = state.get("worker_trace", []) + ["records_worker"]
    return {"logs": events, "worker_trace": trace}


def resolution_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    system = (
        "Recommend HR resolution steps. Return JSON: recommendation, runbook_id, citations. "
        "Base on HR policy context and HRIS event history only."
    )
    user = json.dumps(
        {"alert": alert, "runbook_context": state.get("runbook_context", ""), "events": state.get("logs", [])}
    )
    raw = call_llm(system, user)
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        chunks = state.get("runbook_chunks") or []
        data = {"recommendation": raw, "runbook_id": chunks[0]["runbook_id"] if chunks else "unknown", "citations": []}
    rec = data.get("recommendation", "")
    requires_hitl = state.get("requires_hitl", False) or any(k in rec.lower() for k in SENSITIVE_HR_KEYWORDS)
    trace = state.get("worker_trace", []) + ["resolution_worker"]
    return {
        "recommendation": rec,
        "runbook_id": data.get("runbook_id", "unknown"),
        "requires_hitl": requires_hitl,
        "worker_trace": trace,
    }


def case_closure_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    if state.get("requires_hitl") and not state.get("hitl_approved"):
        trace = state.get("worker_trace", []) + ["case_closure_worker:pending_hitl"]
        return {
            "ticket": {"status": "pending_hitl"},
            "final_response": state.get("recommendation", ""),
            "worker_trace": trace,
        }
    ticket = create_ticket(
        alert.get("service", ""),
        alert.get("severity", "P3"),
        state.get("recommendation", ""),
        state.get("runbook_id", "unknown"),
    )
    trace = state.get("worker_trace", []) + ["case_closure_worker"]
    final = f"HR resolution: {state.get('recommendation', '')}. Case: {ticket.get('ticket_id')}"
    return {"ticket": ticket, "final_response": final, "worker_trace": trace}


def hitl_gate(state: dict) -> dict:
    return {}
