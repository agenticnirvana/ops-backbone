"""Internal knowledge agent — answers from company policy/docs RAG (bundled dummy corpus)."""

from __future__ import annotations

import json
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.llm import call_llm
from agent.state import AgentState
from agent.tools.fixture_events import query_fixture_events
from agent.tools.runbook_rag import format_runbook_context, retrieve_runbooks
from agent.tools.ticket_create import create_ticket

SENSITIVE_KEYWORDS = ("export", "pii", "personal laptop", "bulk", "salary", "confidential", "usb")


def classify_query_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    system = (
        "Classify the internal employee request. Return JSON: "
        "classification (policy_question|security_request|other), requires_hitl (bool)."
    )
    raw = call_llm(system, json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        text = f"{alert.get('error_summary', '')} {alert.get('log_snippet', '')}".lower()
        data = {
            "classification": "security_request" if "export" in text or "pii" in text else "policy_question",
            "requires_hitl": any(k in text for k in SENSITIVE_KEYWORDS),
        }
    requires = bool(data.get("requires_hitl")) or alert.get("severity") in ("P1", "P0")
    return {
        "classification": data.get("classification", "other"),
        "requires_hitl": requires,
    }


def retrieve_docs_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    service = alert.get("service", "")
    query = f"{service} {alert.get('error_summary', '')} {alert.get('log_snippet', '')}"
    chunks = retrieve_runbooks(query, service=service, domain="internal", top_k=4)
    events = query_fixture_events("internal", service, query)
    return {
        "runbook_chunks": chunks,
        "runbook_context": format_runbook_context(chunks),
        "logs": events,
    }


def answer_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    system = (
        "Answer the employee using internal policy documents only. Return JSON: "
        "recommendation (string answer), runbook_id (primary doc id), citations (list)."
    )
    user = json.dumps(
        {
            "alert": alert,
            "policy_context": state.get("runbook_context", ""),
            "recent_activity": state.get("logs", []),
        }
    )
    raw = call_llm(system, user)
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        chunks = state.get("runbook_chunks") or []
        data = {"recommendation": raw, "runbook_id": chunks[0]["runbook_id"] if chunks else "unknown", "citations": []}
    rec = data.get("recommendation", "")
    requires_hitl = state.get("requires_hitl", False) or any(k in rec.lower() for k in SENSITIVE_KEYWORDS)
    return {
        "recommendation": rec,
        "runbook_id": data.get("runbook_id", "unknown"),
        "requires_hitl": requires_hitl,
    }


def hitl_gate_node(state: AgentState) -> AgentState:
    return {}


def log_case_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    if state.get("requires_hitl") and not state.get("hitl_approved"):
        return {"ticket": {"status": "pending_hitl", "message": "Sensitive request awaiting approval"}}
    ticket = create_ticket(
        alert.get("service", ""),
        alert.get("severity", "P3"),
        state.get("recommendation", ""),
        state.get("runbook_id", "unknown"),
    )
    return {"ticket": ticket}


def route_after_answer(state: AgentState) -> Literal["hitl_gate", "log_case"]:
    if state.get("requires_hitl"):
        return "hitl_gate"
    return "log_case"


def route_after_hitl(state: AgentState) -> Literal["log_case", "end"]:
    if state.get("hitl_approved"):
        return "log_case"
    return "end"


def build_internal_graph(*, enable_hitl: bool = True):
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify_query_node)
    graph.add_node("retrieve_docs", retrieve_docs_node)
    graph.add_node("answer", answer_node)
    graph.add_node("hitl_gate", hitl_gate_node)
    graph.add_node("log_case", log_case_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve_docs")
    graph.add_edge("retrieve_docs", "answer")
    graph.add_conditional_edges("answer", route_after_answer, {"hitl_gate": "hitl_gate", "log_case": "log_case"})
    graph.add_conditional_edges("hitl_gate", route_after_hitl, {"log_case": "log_case", "end": END})
    graph.add_edge("log_case", END)

    memory = MemorySaver()
    interrupt = ["hitl_gate"] if enable_hitl else []
    return graph.compile(checkpointer=memory, interrupt_before=interrupt)


_internal_graph = None


def get_internal_graph():
    global _internal_graph
    if _internal_graph is None:
        _internal_graph = build_internal_graph()
    return _internal_graph
