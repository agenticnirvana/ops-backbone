"""Agent state schema."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AlertInput(TypedDict, total=False):
    service: str
    severity: str
    error_summary: str
    log_snippet: str
    thread_id: str


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    alert: AlertInput
    classification: str
    runbook_chunks: list[dict]
    runbook_context: str
    recommendation: str
    runbook_id: str
    runbook_match: dict
    runbook_gap: bool
    requires_hitl: bool
    hitl_approved: bool
    hitl_approver: str
    ticket: dict
    logs: list[dict]
    metrics: dict
    policy_allowed: bool
    policy_reason: str
    mcp_tool_calls: list[dict]
