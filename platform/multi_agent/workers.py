"""Specialist worker nodes invoked by supervisor."""

from __future__ import annotations

import json

from agent.llm import call_llm
from agent.tools.log_query import query_logs
from agent.tools.runbook_rag import format_runbook_context, retrieve_runbooks
from agent.tools.ticket_create import create_ticket
from observability.trace_context import trace_graph_node

DESTRUCTIVE_KEYWORDS = ("restart", "rollback", "kill", "delete", "scale-down")


@trace_graph_node("triage_worker", multi=True)
def triage_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    system = "Classify the alert. Return JSON: classification (string), requires_hitl (bool)."
    raw = call_llm(system, json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        data = {"classification": "unknown", "requires_hitl": alert.get("severity") in ("P1", "P0")}
    trace = state.get("worker_trace", []) + ["triage_worker"]
    return {
        "classification": data.get("classification", "unknown"),
        "requires_hitl": bool(data.get("requires_hitl")) or alert.get("severity") in ("P1", "P0"),
        "worker_trace": trace,
    }


@trace_graph_node("runbook_worker", multi=True)
def runbook_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    service = alert.get("service", "")
    query = f"{service} {alert.get('error_summary', '')} {alert.get('log_snippet', '')}"
    chunks = retrieve_runbooks(query, service=service, top_k=3)
    trace = state.get("worker_trace", []) + ["runbook_worker"]
    return {
        "runbook_chunks": chunks,
        "runbook_context": format_runbook_context(chunks),
        "worker_trace": trace,
    }


@trace_graph_node("logs_worker", multi=True)
def logs_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    logs = query_logs(alert.get("service", ""), alert.get("error_summary", ""))
    trace = state.get("worker_trace", []) + ["logs_worker"]
    return {"logs": logs, "worker_trace": trace}


@trace_graph_node("metrics_worker", multi=True)
def metrics_worker(state: dict) -> dict:
    from agent.tools.metrics_query import query_metrics

    alert = state.get("alert", {})
    metrics = query_metrics(alert.get("service", ""))
    trace = state.get("worker_trace", []) + ["metrics_worker"]
    return {"metrics": metrics, "worker_trace": trace}


@trace_graph_node("observability_worker", multi=True)
def observability_worker(state: dict) -> dict:
    """Legacy combined worker — kept for tests."""
    alert = state.get("alert", {})
    logs = query_logs(alert.get("service", ""), alert.get("error_summary", ""))
    trace = state.get("worker_trace", []) + ["observability_worker"]
    return {"logs": logs, "worker_trace": trace}


@trace_graph_node("remediation_worker", multi=True)
def remediation_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    system = (
        "Recommend remediation. Return JSON: recommendation, runbook_id, citations."
        " Base on runbook_context and logs only."
    )
    user = json.dumps(
        {
            "alert": alert,
            "runbook_context": state.get("runbook_context", ""),
            "logs": state.get("logs", []),
            "metrics": state.get("metrics", {}),
        }
    )
    raw = call_llm(system, user)
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        chunks = state.get("runbook_chunks") or []
        data = {"recommendation": raw, "runbook_id": chunks[0]["runbook_id"] if chunks else "unknown", "citations": []}
    rec = data.get("recommendation", "")
    requires_hitl = state.get("requires_hitl", False) or any(k in rec.lower() for k in DESTRUCTIVE_KEYWORDS)
    trace = state.get("worker_trace", []) + ["remediation_worker"]
    return {
        "recommendation": rec,
        "runbook_id": data.get("runbook_id", "unknown"),
        "requires_hitl": requires_hitl,
        "worker_trace": trace,
    }


@trace_graph_node("incident_worker", multi=True)
def incident_worker(state: dict) -> dict:
    alert = state.get("alert", {})
    if state.get("requires_hitl") and not state.get("hitl_approved"):
        trace = state.get("worker_trace", []) + ["incident_worker:pending_hitl"]
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
    trace = state.get("worker_trace", []) + ["incident_worker"]
    final = f"Recommendation: {state.get('recommendation', '')}. Ticket: {ticket.get('ticket_id')}"
    return {"ticket": ticket, "final_response": final, "worker_trace": trace}


@trace_graph_node("hitl_gate", multi=True)
def hitl_gate(state: dict) -> dict:
    return {}
