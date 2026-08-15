"""HR multi-agent supervisor graph — corporate onboarding / comp cases."""

from __future__ import annotations

import json
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.llm import call_llm
from multi_agent.hr_workers import (
    case_closure_worker,
    case_triage_worker,
    hitl_gate,
    policy_worker,
    records_worker,
    resolution_worker,
)
from multi_agent.state import MultiAgentState


def hr_supervisor_node(state: MultiAgentState) -> MultiAgentState:
    alert = state.get("alert", {})
    system = (
        "You are an HR operations supervisor. Return JSON with route: "
        "'full_pipeline' for P1/P2 cases or 'fast_path' for P3 informational cases."
    )
    raw = call_llm(system, json.dumps(alert))
    try:
        data = json.loads(raw.strip().strip("`").replace("json", ""))
        route = data.get("route", "full_pipeline")
    except json.JSONDecodeError:
        route = "fast_path" if alert.get("severity") == "P3" else "full_pipeline"
    return {"route": route, "worker_trace": ["hr_supervisor:" + route]}


def route_after_resolution(state: MultiAgentState) -> Literal["hitl_gate", "case_closure_worker"]:
    if state.get("requires_hitl"):
        return "hitl_gate"
    return "case_closure_worker"


def route_after_hitl(state: MultiAgentState) -> Literal["case_closure_worker", "end"]:
    if state.get("hitl_approved"):
        return "case_closure_worker"
    return "end"


def build_hr_multi_agent_graph(*, enable_hitl: bool = True):
    """
    HR topology:
    supervisor → case_triage → policy → records → resolution → [hitl] → case_closure
    """
    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", hr_supervisor_node)
    graph.add_node("case_triage_worker", case_triage_worker)
    graph.add_node("policy_worker", policy_worker)
    graph.add_node("records_worker", records_worker)
    graph.add_node("resolution_worker", resolution_worker)
    graph.add_node("hitl_gate", hitl_gate)
    graph.add_node("case_closure_worker", case_closure_worker)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "case_triage_worker")
    graph.add_edge("case_triage_worker", "policy_worker")
    graph.add_edge("policy_worker", "records_worker")
    graph.add_edge("records_worker", "resolution_worker")
    graph.add_conditional_edges(
        "resolution_worker",
        route_after_resolution,
        {"hitl_gate": "hitl_gate", "case_closure_worker": "case_closure_worker"},
    )
    graph.add_conditional_edges(
        "hitl_gate",
        route_after_hitl,
        {"case_closure_worker": "case_closure_worker", "end": END},
    )
    graph.add_edge("case_closure_worker", END)

    memory = MemorySaver()
    interrupt = ["hitl_gate"] if enable_hitl else []
    return graph.compile(checkpointer=memory, interrupt_before=interrupt)


_hr_graph = None


def get_hr_multi_agent_graph():
    global _hr_graph
    if _hr_graph is None:
        _hr_graph = build_hr_multi_agent_graph()
    return _hr_graph
