"""LangGraph ops incident triage agent — Design 1 (Chroma + Loki + Prometheus)."""

from __future__ import annotations

import json
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.guardrails import validate_alert_input
from agent.llm import call_llm
from agent.state import AgentState
from observability.trace_context import trace_graph_node
from agent.tools.log_query import query_logs
from agent.tools.metrics_query import query_metrics
from agent.tools.policy_check import check_action_allowed
from agent.tools.runbook_rag import retrieve_with_gate, unmatched_recommendation
from agent.tools.ticket_create import create_ticket

DESTRUCTIVE_KEYWORDS = ("restart", "rollback", "kill", "delete", "scale-down")


@trace_graph_node("classify")
def classify_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    ok, reason = validate_alert_input(alert)
    if not ok:
        return {
            "classification": "blocked",
            "requires_hitl": False,
            "recommendation": reason,
            "runbook_id": "none",
        }
    system = "Classify the alert. Return JSON: classification (string), requires_hitl (bool)."
    user = json.dumps(alert)
    raw = call_llm(system, user)
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        severity = alert.get("severity", "P3")
        data = {
            "classification": "unknown",
            "requires_hitl": severity in ("P1", "P0"),
        }
    return {
        "classification": data.get("classification", "unknown"),
        "requires_hitl": bool(data.get("requires_hitl")) or alert.get("severity") in ("P1", "P0"),
    }


@trace_graph_node("retrieve_runbook")
def retrieve_runbook_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    service = alert.get("service", "")
    query = f"{service} {alert.get('error_summary', '')} {alert.get('log_snippet', '')}".strip()
    gated = retrieve_with_gate(query, service=service, top_k=3)
    return {
        "runbook_chunks": gated["chunks"],
        "runbook_context": gated["context"],
        "runbook_match": gated["match"],
        "runbook_gap": gated["gap"],
        "runbook_id": gated["runbook_id"],
    }


@trace_graph_node("query_logs")
def query_logs_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    logs = query_logs(alert.get("service", ""), alert.get("error_summary", ""))
    return {"logs": logs}


@trace_graph_node("query_metrics")
def query_metrics_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    metrics = query_metrics(alert.get("service", ""))
    return {"metrics": metrics}


@trace_graph_node("recommend")
def recommend_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    match = state.get("runbook_match") or {}
    grounded = bool(match.get("matched"))
    if grounded:
        system = (
            "Recommend remediation for the ops alert. Return JSON: "
            "recommendation (string), runbook_id (string), citations (list of source files). "
            "Base recommendation ONLY on the runbook context, logs, and metrics provided."
        )
    else:
        system = (
            "There is NO grounded runbook for this alert. Do not invent or reuse a catalog runbook_id. "
            "Return JSON: recommendation (investigation steps the operator should take), "
            "runbook_id (must be the string none), citations (empty list), runbook_gap (true)."
        )
    user = json.dumps(
        {
            "alert": alert,
            "runbook_context": state.get("runbook_context", ""),
            "runbook_match": match,
            "logs": state.get("logs", []),
            "metrics": state.get("metrics", {}),
        }
    )
    raw = call_llm(system, user)
    try:
        data = json.loads(raw.strip().strip("`").replace("json", "", 1))
    except json.JSONDecodeError:
        chunks = state.get("runbook_chunks") or []
        rb_id = chunks[0]["runbook_id"] if grounded and chunks else "none"
        data = {"recommendation": raw, "runbook_id": rb_id, "citations": []}

    if grounded:
        chunks = state.get("runbook_chunks") or []
        if chunks:
            data["runbook_id"] = chunks[0]["runbook_id"]
            if not data.get("citations"):
                data["citations"] = [chunks[0].get("source", f"{chunks[0]['runbook_id']}.md")]
        rec = data.get("recommendation", "")
    else:
        data["runbook_id"] = "none"
        rec = data.get("recommendation") or unmatched_recommendation(alert=alert, match=match)

    metrics = state.get("metrics") or {}
    high_error_rate = float(metrics.get("error_rate_5m") or 0.0) >= 0.05
    requires_hitl = (
        state.get("requires_hitl", False)
        or any(k in rec.lower() for k in DESTRUCTIVE_KEYWORDS)
        or high_error_rate
        or not grounded
    )
    return {
        "recommendation": rec,
        "runbook_id": data.get("runbook_id", "none" if not grounded else "unknown"),
        "requires_hitl": requires_hitl,
        "runbook_gap": not grounded,
        "runbook_match": match,
    }


@trace_graph_node("hitl_gate")
def hitl_gate_node(state: AgentState) -> AgentState:
    """Pass-through; interrupt_before pauses here for human approval."""
    from observability.trace_context import emit_event

    paused = bool(state.get("requires_hitl") and not state.get("hitl_approved"))
    emit_event(
        "🛡️ Event · HITL interrupt" if paused else "🛡️ Event · HITL skip",
        input={
            "requires_hitl": bool(state.get("requires_hitl")),
            "severity": (state.get("alert") or {}).get("severity"),
        },
        output={"paused": paused, "approved": bool(state.get("hitl_approved"))},
        metadata={"phase": "4-guardrails", "node": "hitl_gate"},
        level="WARNING" if paused else "DEFAULT",
    )
    return {}


@trace_graph_node("execute")
def execute_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    if state.get("requires_hitl") and not state.get("hitl_approved"):
        return {"ticket": {"status": "pending_hitl", "message": "Awaiting human approval"}}

    allowed, reason = check_action_allowed(
        service=alert.get("service", ""),
        recommendation=state.get("recommendation", ""),
        severity=alert.get("severity", "P3"),
    )
    if not allowed:
        return {
            "policy_allowed": False,
            "policy_reason": reason,
            "ticket": {"status": "blocked_by_policy", "message": reason},
        }

    ticket = create_ticket(
        alert.get("service", ""),
        alert.get("severity", "P3"),
        state.get("recommendation", ""),
        state.get("runbook_id", "unknown"),
        approved_by=state.get("hitl_approver"),
    )
    from observability.trace_context import emit_event

    emit_event(
        "🎫 Event · Ticket created",
        input={"service": alert.get("service"), "runbook_id": state.get("runbook_id")},
        output={"ticket_id": ticket.get("ticket_id"), "status": ticket.get("status")},
        metadata={"phase": "5-action", "node": "execute"},
    )
    return {"policy_allowed": True, "policy_reason": reason, "ticket": ticket}


def route_after_recommend(state: AgentState) -> Literal["hitl_gate", "execute"]:
    if state.get("requires_hitl"):
        return "hitl_gate"
    return "execute"


def route_after_hitl(state: AgentState) -> Literal["execute", "end"]:
    if state.get("hitl_approved"):
        return "execute"
    return "end"


def build_graph(*, enable_hitl: bool = True):
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve_runbook", retrieve_runbook_node)
    graph.add_node("query_logs", query_logs_node)
    graph.add_node("query_metrics", query_metrics_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("hitl_gate", hitl_gate_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve_runbook")
    graph.add_edge("retrieve_runbook", "query_logs")
    graph.add_edge("query_logs", "query_metrics")
    graph.add_edge("query_metrics", "recommend")
    graph.add_conditional_edges("recommend", route_after_recommend, {"hitl_gate": "hitl_gate", "execute": "execute"})
    graph.add_conditional_edges("hitl_gate", route_after_hitl, {"execute": "execute", "end": END})
    graph.add_edge("execute", END)

    memory = MemorySaver()
    interrupt = ["hitl_gate"] if enable_hitl else []
    return graph.compile(checkpointer=memory, interrupt_before=interrupt)


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
