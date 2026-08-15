"""FastAPI service for ops triage agent."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.graph import get_graph
from agent.guardrails import validate_alert_input
from notifications.slack import notify_hitl_required
from observability.dashboard_metrics import record_run_finish as persist_run_finish
from observability.dashboard_metrics import record_run_start as persist_run_start
from observability.setup import build_invoke_config, setup_mlflow_tracing, setup_otel


class AlertPayload(BaseModel):
    service: str
    severity: str = "P3"
    error_summary: str
    log_snippet: str = ""
    thread_id: str | None = None
    design_id: str | None = None


class InvokeResponse(BaseModel):
    thread_id: str
    classification: str | None = None
    recommendation: str | None = None
    runbook_id: str | None = None
    requires_hitl: bool = False
    hitl_approved: bool = False
    ticket: dict[str, Any] | None = None
    runbook_chunks: list[dict] | None = None
    status: str = "completed"
    service: str | None = None
    severity: str | None = None
    error_summary: str | None = None


class ApprovePayload(BaseModel):
    thread_id: str
    approved: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel()
    setup_mlflow_tracing()
    from rag.indexer import active_manifest_path

    if not active_manifest_path().is_file():
        raise RuntimeError(
            "Runbook index not ready. Start runbook-ingestion service or run a reindex job first."
        )
    yield


app = FastAPI(title="Ops Triage Agent", version=os.getenv("GRAPH_VERSION", "1.0.0"), lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "graph_version": os.getenv("GRAPH_VERSION", "1.0.0")}


@app.get("/ready")
def ready():
    graph = get_graph()
    return {"status": "ready" if graph else "not_ready"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(payload: AlertPayload):
    thread_id = payload.thread_id or str(uuid.uuid4())
    alert = payload.model_dump()
    ok, reason = validate_alert_input(alert)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    graph = get_graph()
    config = build_invoke_config("ops-triage-invoke", session_id=thread_id, design_id=payload.design_id)
    persist_run_start(
        thread_id=thread_id,
        mode="standalone",
        domain="sre",
        service=payload.service,
        severity=payload.severity,
        status="running",
        source="agent-api",
    )
    try:
        result = graph.invoke({"alert": alert}, config=config)
    except Exception as exc:
        persist_run_finish(thread_id=thread_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    interrupted = graph.get_state(config).next
    status = "awaiting_hitl" if interrupted else "completed"
    if status == "awaiting_hitl":
        persist_run_start(
            thread_id=thread_id,
            mode="standalone",
            domain="sre",
            service=payload.service,
            severity=payload.severity,
            status="awaiting_hitl",
            runbook_id=result.get("runbook_id"),
            source="agent-api",
            hitl_required=True,
        )
        notify_hitl_required(
            thread_id=thread_id,
            service=payload.service,
            severity=payload.severity,
            recommendation=result.get("recommendation"),
            runbook_id=result.get("runbook_id"),
            source="agent-api",
        )
    else:
        ticket = result.get("ticket") or {}
        persist_run_finish(
            thread_id=thread_id,
            status="completed",
            runbook_id=result.get("runbook_id"),
            ticket_id=ticket.get("id") or ticket.get("ticket_id"),
            hitl_required=bool(result.get("requires_hitl")),
        )
    return InvokeResponse(
        thread_id=thread_id,
        classification=result.get("classification"),
        recommendation=result.get("recommendation"),
        runbook_id=result.get("runbook_id"),
        requires_hitl=result.get("requires_hitl", False),
        hitl_approved=result.get("hitl_approved", False),
        ticket=result.get("ticket"),
        runbook_chunks=result.get("runbook_chunks"),
        status=status,
    )


@app.get("/state/{thread_id}", response_model=InvokeResponse)
def get_state(thread_id: str):
    graph = get_graph()
    config = build_invoke_config("ops-triage-invoke", session_id=thread_id)
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    result = state.values
    status = "awaiting_hitl" if state.next else "completed"
    alert = result.get("alert") or {}
    return InvokeResponse(
        thread_id=thread_id,
        classification=result.get("classification"),
        recommendation=result.get("recommendation"),
        runbook_id=result.get("runbook_id"),
        requires_hitl=result.get("requires_hitl", False),
        hitl_approved=result.get("hitl_approved", False),
        ticket=result.get("ticket"),
        runbook_chunks=result.get("runbook_chunks"),
        status=status,
        service=alert.get("service"),
        severity=alert.get("severity"),
        error_summary=alert.get("error_summary"),
    )


@app.post("/approve", response_model=InvokeResponse)
def approve(payload: ApprovePayload):
    if not payload.approved:
        raise HTTPException(status_code=400, detail="Approval denied")
    graph = get_graph()
    config = build_invoke_config("ops-triage-invoke", session_id=payload.thread_id)
    checkpoint = graph.get_state(config)
    if not checkpoint.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    if not checkpoint.next:
        state = checkpoint
        result = state.values
        return InvokeResponse(
            thread_id=payload.thread_id,
            classification=result.get("classification"),
            recommendation=result.get("recommendation"),
            runbook_id=result.get("runbook_id"),
            requires_hitl=result.get("requires_hitl", False),
            hitl_approved=bool(result.get("hitl_approved")),
            ticket=result.get("ticket"),
            runbook_chunks=result.get("runbook_chunks"),
            status="completed",
        )
    graph.update_state(config, {"hitl_approved": True, "hitl_approver": os.getenv("HITL_APPROVER", "agent-api")})
    try:
        graph.invoke(None, config=config)
    except Exception as exc:
        persist_run_finish(thread_id=payload.thread_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    state = graph.get_state(config)
    result = state.values
    status = "awaiting_hitl" if state.next else "completed"
    if status == "completed":
        ticket = result.get("ticket") or {}
        persist_run_finish(
            thread_id=payload.thread_id,
            status="completed",
            runbook_id=result.get("runbook_id"),
            ticket_id=ticket.get("id") or ticket.get("ticket_id"),
            hitl_required=bool(result.get("requires_hitl")),
        )
    return InvokeResponse(
        thread_id=payload.thread_id,
        classification=result.get("classification"),
        recommendation=result.get("recommendation"),
        runbook_id=result.get("runbook_id"),
        requires_hitl=result.get("requires_hitl", False),
        hitl_approved=bool(result.get("hitl_approved")),
        ticket=result.get("ticket"),
        runbook_chunks=result.get("runbook_chunks"),
        status=status,
    )
