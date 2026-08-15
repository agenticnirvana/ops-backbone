"""Multi-agent state for supervisor orchestration."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class MultiAgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    alert: dict
    route: str
    classification: str
    runbook_context: str
    runbook_chunks: list[dict]
    logs: list[dict]
    metrics: dict
    recommendation: str
    runbook_id: str
    requires_hitl: bool
    hitl_approved: bool
    ticket: dict
    worker_trace: list[str]
    delegation_events: list[dict]
    final_response: str
