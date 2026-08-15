"""Supervisor orchestrator — routes alert through specialist workers."""

from __future__ import annotations

import json
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.llm import call_llm
from multi_agent.state import MultiAgentState
from observability.trace_context import trace_graph_node
from multi_agent.workers import (
    hitl_gate,
    incident_worker,
    logs_worker,
    metrics_worker,
    remediation_worker,
    runbook_worker,
    triage_worker,
)


@trace_graph_node("supervisor", multi=True)
def supervisor_node(state: MultiAgentState) -> MultiAgentState:
    """Supervisor decides execution plan and delegates to specialist workers."""
    alert = state.get("alert", {})
    system = (
        "You are an AIOps supervisor. Given an alert, return JSON with route: "
        "'full_pipeline' (always use for P1/P2) or 'fast_path' (P3 only)."
    )
    raw = call_llm(system, json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
        route = data.get("route", "full_pipeline")
    except json.JSONDecodeError:
        route = "fast_path" if alert.get("severity") == "P3" else "full_pipeline"
    service = alert.get("service", "service")
    trace = [f"supervisor:{route}"]
    delegations = [
        {
            "from": "supervisor",
            "to": "triage_worker",
            "message": f"Delegate classification for {service} ({route})",
        }
    ]
    return {"route": route, "worker_trace": trace, "delegation_events": delegations}


def _append_delegation(state: MultiAgentState, worker: str, next_worker: str | None, message: str) -> list[dict]:
    events = list(state.get("delegation_events") or [])
    events.append({"from": worker, "to": next_worker or "end", "message": message})
    return events


def triage_worker_with_delegation(state: MultiAgentState) -> MultiAgentState:
    result = triage_worker(state)
    result["delegation_events"] = _append_delegation(
        {**state, **result},
        "triage_worker",
        "runbook_worker",
        "Fetch runbook context via Chroma RAG",
    )
    return result


def runbook_worker_with_delegation(state: MultiAgentState) -> MultiAgentState:
    result = runbook_worker(state)
    result["delegation_events"] = _append_delegation(
        {**state, **result},
        "runbook_worker",
        "logs_worker",
        "Investigate logs in Loki",
    )
    return result


def logs_worker_with_delegation(state: MultiAgentState) -> MultiAgentState:
    result = logs_worker(state)
    result["delegation_events"] = _append_delegation(
        {**state, **result},
        "logs_worker",
        "metrics_worker",
        "Pull Prometheus metrics for anomaly confirmation",
    )
    return result


def metrics_worker_with_delegation(state: MultiAgentState) -> MultiAgentState:
    result = metrics_worker(state)
    result["delegation_events"] = _append_delegation(
        {**state, **result},
        "metrics_worker",
        "remediation_worker",
        "Synthesize remediation plan from runbook + observability",
    )
    return result


def remediation_worker_with_delegation(state: MultiAgentState) -> MultiAgentState:
    result = remediation_worker(state)
    nxt = "hitl_gate" if result.get("requires_hitl") else "incident_worker"
    result["delegation_events"] = _append_delegation(
        {**state, **result},
        "remediation_worker",
        nxt,
        "Route to HITL or ticket creation",
    )
    return result


def route_after_remediation(state: MultiAgentState) -> Literal["hitl_gate", "incident_worker"]:
    if state.get("requires_hitl"):
        return "hitl_gate"
    return "incident_worker"


def route_after_hitl(state: MultiAgentState) -> Literal["incident_worker", "end"]:
    if state.get("hitl_approved"):
        return "incident_worker"
    return "end"


def build_multi_agent_graph(*, enable_hitl: bool = True):
    """
    Multi-agent topology:
    supervisor → triage → runbook → logs → metrics → remediation → [hitl] → incident
    """
    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("triage_worker", triage_worker_with_delegation)
    graph.add_node("runbook_worker", runbook_worker_with_delegation)
    graph.add_node("logs_worker", logs_worker_with_delegation)
    graph.add_node("metrics_worker", metrics_worker_with_delegation)
    graph.add_node("remediation_worker", remediation_worker_with_delegation)
    graph.add_node("hitl_gate", hitl_gate)
    graph.add_node("incident_worker", incident_worker)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "triage_worker")
    graph.add_edge("triage_worker", "runbook_worker")
    graph.add_edge("runbook_worker", "logs_worker")
    graph.add_edge("logs_worker", "metrics_worker")
    graph.add_edge("metrics_worker", "remediation_worker")
    graph.add_conditional_edges(
        "remediation_worker",
        route_after_remediation,
        {"hitl_gate": "hitl_gate", "incident_worker": "incident_worker"},
    )
    graph.add_conditional_edges(
        "hitl_gate",
        route_after_hitl,
        {"incident_worker": "incident_worker", "end": END},
    )
    graph.add_edge("incident_worker", END)

    memory = MemorySaver()
    interrupt = ["hitl_gate"] if enable_hitl else []
    return graph.compile(checkpointer=memory, interrupt_before=interrupt)


_graph = None


def get_multi_agent_graph():
    global _graph
    if _graph is None:
        _graph = build_multi_agent_graph()
    return _graph
