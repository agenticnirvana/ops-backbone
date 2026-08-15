"""MCP-backed agent — tools invoked via hosted HTTP MCP server (Basic Auth)."""

from __future__ import annotations

import json
import os
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.llm import call_llm
from agent.state import AgentState
from mcp_server.tools_impl import (
    mcp_create_ticket,
    mcp_get_metrics,
    mcp_query_logs,
    mcp_retrieve_runbooks,
)


def _use_mcp_tools() -> bool:
    return os.getenv("USE_MCP_TOOLS", "false").lower() == "true"


def _tool_calls(state: AgentState) -> list[dict]:
    return list(state.get("mcp_tool_calls") or [])


def _retrieve(alert: dict, calls: list[dict]) -> tuple[list, str, dict]:
    service = alert.get("service", "")
    query = f"{service} {alert.get('error_summary', '')} {alert.get('log_snippet', '')}".strip()
    from agent.tools.runbook_rag import (
        assess_runbook_match,
        format_runbook_context,
        retrieve_with_gate,
    )

    if _use_mcp_tools():
        data = mcp_retrieve_runbooks(query, service=service, top_k=3, calls=calls)
        chunks = data.get("chunks") or []
        match = assess_runbook_match(chunks, query=query, service=service)
        if match["matched"]:
            return chunks, data.get("context") or format_runbook_context(chunks), match
        nearest = (match.get("nearest") or {}).get("runbook_id") or "none"
        pct = int(round(float(match.get("similarity") or 0) * 100))
        ctx = (
            "No grounded runbook. Do not follow a nearest-neighbor document. "
            f"Rejected candidate: {nearest} at {pct}% similarity."
        )
        return chunks, ctx, match
    gated = retrieve_with_gate(query, service=service, top_k=3)
    return gated["chunks"], gated["context"], gated["match"]


def classify_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    raw = call_llm("Classify alert. JSON: classification, requires_hitl.", json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        data = {"classification": "unknown", "requires_hitl": alert.get("severity") in ("P1", "P0")}
    return {
        "classification": data.get("classification", "unknown"),
        "requires_hitl": bool(data.get("requires_hitl")) or alert.get("severity") in ("P1", "P0"),
    }


def retrieve_node(state: AgentState) -> AgentState:
    calls = _tool_calls(state)
    chunks, ctx, match = _retrieve(state.get("alert", {}), calls)
    grounded = bool(match.get("matched"))
    return {
        "runbook_chunks": chunks,
        "runbook_context": ctx,
        "runbook_match": match,
        "runbook_gap": not grounded,
        "runbook_id": match.get("runbook_id") if grounded else "none",
        "mcp_tool_calls": calls,
    }


def metrics_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    service = alert.get("service", "")
    calls = _tool_calls(state)
    if _use_mcp_tools():
        metrics = mcp_get_metrics(service, calls=calls)
        logs = mcp_query_logs(service, alert.get("error_summary", ""), calls=calls)
    else:
        from agent.tools.log_query import query_logs

        metrics = {"note": "in-process mode"}
        logs = query_logs(service, alert.get("error_summary", ""))
    return {
        "logs": logs,
        "metrics": metrics,
        "mcp_tool_calls": calls,
        "classification": f"{state.get('classification', '')}|metrics:{metrics.get('cpu_percent', 'n/a')}",
    }


def recommend_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    match = state.get("runbook_match") or {}
    grounded = bool(match.get("matched"))
    if grounded:
        system = "Recommend remediation. JSON: recommendation, runbook_id, citations."
    else:
        system = (
            "There is NO grounded runbook for this alert. Do not invent or reuse a catalog runbook_id. "
            "Return JSON: recommendation (investigation steps), runbook_id (must be the string none), "
            "citations (empty list), runbook_gap (true)."
        )
    raw = call_llm(
        system,
        json.dumps({
            "alert": alert,
            "runbook_context": state.get("runbook_context", ""),
            "runbook_match": match,
            "logs": state.get("logs", []),
            "metrics": state.get("metrics", {}),
        }),
    )
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
    except json.JSONDecodeError:
        data = {"recommendation": raw, "runbook_id": "none" if not grounded else "unknown", "citations": []}
    rec = data.get("recommendation", "")
    if not grounded:
        from agent.tools.runbook_rag import unmatched_recommendation

        data["runbook_id"] = "none"
        rec = rec or unmatched_recommendation(alert=alert, match=match)
    hitl = (
        state.get("requires_hitl")
        or any(k in rec.lower() for k in ("restart", "kill", "rollback"))
        or not grounded
    )
    return {
        "recommendation": rec,
        "runbook_id": data.get("runbook_id") if grounded else "none",
        "requires_hitl": hitl,
        "runbook_gap": not grounded,
        "runbook_match": match,
    }


def execute_node(state: AgentState) -> AgentState:
    alert = state.get("alert", {})
    if state.get("requires_hitl") and not state.get("hitl_approved"):
        return {"ticket": {"status": "pending_hitl"}}
    calls = _tool_calls(state)
    if _use_mcp_tools():
        ticket = mcp_create_ticket(
            alert.get("service", ""),
            alert.get("severity", "P3"),
            state.get("recommendation", ""),
            state.get("runbook_id", "unknown"),
            calls=calls,
        )
    else:
        from agent.tools.ticket_create import create_ticket

        ticket = create_ticket(
            alert.get("service", ""),
            alert.get("severity", "P3"),
            state.get("recommendation", ""),
            state.get("runbook_id", "unknown"),
        )
    return {"ticket": ticket, "mcp_tool_calls": calls}


def route_hitl(state: AgentState) -> Literal["hitl", "execute"]:
    return "hitl" if state.get("requires_hitl") else "execute"


def hitl_node(state: AgentState) -> AgentState:
    return {}


def route_after_hitl(state: AgentState) -> Literal["execute", "end"]:
    if state.get("hitl_approved"):
        return "execute"
    return "end"


def build_mcp_agent_graph():
    g = StateGraph(AgentState)
    g.add_node("classify", classify_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("metrics", metrics_node)
    g.add_node("recommend", recommend_node)
    g.add_node("hitl", hitl_node)
    g.add_node("execute", execute_node)
    g.set_entry_point("classify")
    g.add_edge("classify", "retrieve")
    g.add_edge("retrieve", "metrics")
    g.add_edge("metrics", "recommend")
    g.add_conditional_edges("recommend", route_hitl, {"hitl": "hitl", "execute": "execute"})
    g.add_conditional_edges("hitl", route_after_hitl, {"execute": "execute", "end": END})
    g.add_edge("execute", END)
    return g.compile(checkpointer=MemorySaver(), interrupt_before=["hitl"])


_mcp_graph = None


def get_mcp_agent_graph():
    global _mcp_graph
    if _mcp_graph is None:
        _mcp_graph = build_mcp_agent_graph()
    return _mcp_graph
