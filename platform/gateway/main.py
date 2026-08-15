"""Unified AIOps Gateway — auth, standalone, multi-agent, MCP modes + UI."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM_ROOT))

import shared.config  # noqa: F401 — sets reference-agent on path

from agent.graph import get_graph as get_standalone_graph
from multi_agent.graph import get_multi_agent_graph
from mcp_server.agent_graph import get_mcp_agent_graph
from gateway.mcp_playground import connect_server, invoke_tool, list_playground_servers
from observability.setup import build_invoke_config, flush_langfuse, setup_mlflow_tracing, setup_otel
from observability.langfuse_api import fetch_langfuse_dashboard, fetch_trace_by_session, record_pipeline_scores
from notifications.slack import notify_hitl_required
from shared.auth import TokenResponse, User, authenticate_user, create_access_token, get_current_user, require_admin, require_roles
from shared.dashboard_metrics import ensure_tables, get_dashboard_stats, list_recent_runs, record_run_finish, record_run_start
from shared.agent_registry import (
    get_registry_agent,
    list_registry_agents,
    register_agent,
    registry_backend,
    registry_public_url,
    seed_agent_registry,
)
from shared.skill_registry import (
    get_skill,
    list_skills,
    mcp_vs_skills_guide,
    registry_backend as skills_registry_backend,
    run_skill_script,
    seed_skills_registry,
)
from shared.hitl_store import list_hitl_decisions, record_hitl_decision
from shared.user_store import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
    change_password,
    create_user,
    delete_user,
    list_users_public,
    update_profile,
    update_user,
    user_counts_by_role,
)
from shared.opa_guardrails import (
    build_evaluation_result,
    get_evaluation_stats,
    list_evaluations,
    list_policy_revisions,
    parse_destructive_keywords,
    read_policy_rego,
    record_evaluation,
    save_policy_rego,
)
from shared.scenarios import list_sre_scenarios
from shared.eval_service import get_eval_dashboard, run_eval_suite
from shared.eval_store import ensure_eval_tables
from shared.alert_flow import get_alert_catalog, simulate_alert_flow
from shared.governance import (
    decide_promotion,
    ensure_governance_tables,
    github_config,
    ingest_github_event,
    list_audit,
    list_pipeline_runs,
    list_promotions,
    overview as governance_overview,
    request_promotion,
)

UI_DIR = PLATFORM_ROOT / "ui"


class LoginRequest(BaseModel):
    email: str
    password: str


class AlertRequest(BaseModel):
    domain: Literal["sre"] = "sre"
    service: str
    severity: str = "P3"
    error_summary: str
    log_snippet: str = ""
    thread_id: str | None = None
    mode: Literal["standalone", "multi", "mcp"] = "standalone"


class AgentResponse(BaseModel):
    domain: str
    mode: str
    thread_id: str
    status: str
    classification: str | None = None
    recommendation: str | None = None
    runbook_id: str | None = None
    requires_hitl: bool = False
    hitl_approved: bool = False
    ticket: dict[str, Any] | None = None
    worker_trace: list[str] | None = None
    delegation_events: list[dict] | None = None
    mcp_tool_calls: list[dict] | None = None
    route: str | None = None
    runbook_chunks: list[dict] | None = None
    runbook_gap: bool = False
    runbook_match: dict | None = None
    final_response: str | None = None
    service: str | None = None
    severity: str | None = None
    error_summary: str | None = None


class PromotionRequest(BaseModel):
    environment: Literal["staging", "production"] = "staging"
    reason: str = ""
    sha: str = ""
    eval_run_id: str | None = None


class PromotionDecideRequest(BaseModel):
    approved: bool
    note: str = ""


class RunbookDraftRequest(BaseModel):
    service: str
    severity: str = "P2"
    error_summary: str
    log_snippet: str = ""
    recommendation: str = ""
    persist: bool = False


class GapTicketRequest(BaseModel):
    service: str
    severity: str = "P2"
    error_summary: str = ""
    recommendation: str = ""


class EvalRunRequest(BaseModel):
    design_id: str | None = None


class IngestReindexRequest(BaseModel):
    mode: Literal["full", "incremental"] = "incremental"
    sync_drive: bool = True


class ApproveRequest(BaseModel):
    thread_id: str
    domain: Literal["sre"] = "sre"
    mode: Literal["standalone", "multi", "mcp"] = "standalone"
    approved: bool = True
    service: str | None = None
    severity: str | None = None
    runbook_id: str | None = None
    recommendation: str | None = None
    opa_allowed: bool | None = None
    opa_rule: str | None = None
    reason: str | None = None


class McpPlaygroundConnect(BaseModel):
    server_id: str
    url: str | None = None
    username: str | None = None
    password: str | None = None


class McpPlaygroundInvoke(BaseModel):
    server_id: str
    tool: str
    payload: dict[str, Any] = {}
    url: str | None = None
    username: str | None = None
    password: str | None = None


class RegisterAgentRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=128)
    kind: Literal["orchestrator", "worker", "mcp_host", "tool"]
    mode: Literal["standalone", "multi", "mcp"]
    description: str = ""
    tools: list[str] | str = ""
    risk_tier: Literal["low", "medium", "high"] = "medium"
    owner: str = "platform-team"
    status: Literal["active", "deprecated", "draft"] = "active"


class SkillRunRequest(BaseModel):
    script: str
    params: list[str] = Field(default_factory=list)


class AlertSimulateRequest(BaseModel):
    alert_id: str | None = None
    invoke_agent: bool = False
    custom_alert: dict[str, Any] | None = None
    design_id: str | None = None


class DashboardRunEvent(BaseModel):
    event: Literal["start", "finish"]
    thread_id: str
    mode: str = "standalone"
    domain: str = "sre"
    service: str | None = None
    severity: str | None = None
    status: str
    runbook_id: str | None = None
    triggered_by: str | None = None
    source: str | None = "agent-api"
    hitl_required: bool = False
    ticket_id: str | None = None
    error_message: str | None = None


def _graph_for_mode(mode: str, domain: str = "sre"):
    if domain != "sre":
        raise HTTPException(status_code=400, detail="Design 1 supports SRE ops only")
    if mode == "multi":
        return get_multi_agent_graph()
    if mode == "mcp":
        return get_mcp_agent_graph()
    return get_standalone_graph()


def _merge_graph_state(graph, config, result: dict | None = None) -> dict:
    checkpoint = graph.get_state(config)
    values = dict(checkpoint.values or {})
    if result:
        values.update(result)
    return values


def _serialize(mode: str, thread_id: str, result: dict, graph, config, domain: str = "sre") -> AgentResponse:
    values = _merge_graph_state(graph, config, result)
    nxt = graph.get_state(config).next
    status = "awaiting_hitl" if nxt else "completed"
    alert = values.get("alert") or {}
    return AgentResponse(
        domain=domain,
        mode=mode,
        thread_id=thread_id,
        status=status,
        classification=values.get("classification"),
        recommendation=values.get("recommendation") or values.get("final_response"),
        runbook_id=values.get("runbook_id"),
        requires_hitl=values.get("requires_hitl", False),
        hitl_approved=bool(values.get("hitl_approved")),
        ticket=values.get("ticket"),
        worker_trace=values.get("worker_trace"),
        delegation_events=values.get("delegation_events"),
        mcp_tool_calls=values.get("mcp_tool_calls"),
        route=values.get("route"),
        runbook_chunks=values.get("runbook_chunks"),
        runbook_gap=bool(values.get("runbook_gap")),
        runbook_match=values.get("runbook_match"),
        final_response=values.get("final_response"),
        service=alert.get("service"),
        severity=alert.get("severity"),
        error_summary=alert.get("error_summary"),
    )


def _ticket_id_from_response(response: AgentResponse) -> str | None:
    ticket = response.ticket
    if not ticket:
        return None
    return ticket.get("ticket_id") or ticket.get("id")


def _persist_run_start(body: AlertRequest, thread_id: str, user_email: str, status: str = "running") -> None:
    record_run_start(
        thread_id=thread_id,
        mode=body.mode,
        domain=body.domain,
        service=body.service,
        severity=body.severity,
        status=status,
        triggered_by=user_email,
        source="platform-ui",
    )


def _persist_run_outcome(thread_id: str, response: AgentResponse, *, error_message: str | None = None) -> None:
    if response.status in ("running", "awaiting_hitl"):
        record_run_start(
            thread_id=thread_id,
            mode=response.mode,
            domain=response.domain,
            service=response.service,
            severity=response.severity,
            status=response.status,
            runbook_id=response.runbook_id,
            source="platform-ui",
            hitl_required=response.status == "awaiting_hitl",
        )
        return
    record_run_finish(
        thread_id=thread_id,
        status=response.status,
        runbook_id=response.runbook_id,
        ticket_id=_ticket_id_from_response(response),
        hitl_required=response.requires_hitl,
        error_message=error_message,
    )


def _notify_hitl_if_needed(body: AlertRequest, response: AgentResponse) -> None:
    if response.status != "awaiting_hitl":
        return
    notify_hitl_required(
        thread_id=response.thread_id,
        service=body.service,
        severity=body.severity,
        recommendation=response.recommendation,
        runbook_id=response.runbook_id,
        source="platform-ui",
    )


def _agent_response_from_json(mode: str, domain: str, data: dict) -> AgentResponse:
    return AgentResponse(
        domain=domain,
        mode=mode,
        thread_id=data["thread_id"],
        status=data.get("status", "completed"),
        classification=data.get("classification"),
        recommendation=data.get("recommendation"),
        runbook_id=data.get("runbook_id"),
        requires_hitl=data.get("requires_hitl", False),
        hitl_approved=data.get("hitl_approved", False),
        ticket=data.get("ticket"),
        runbook_chunks=data.get("runbook_chunks"),
        runbook_gap=bool(data.get("runbook_gap")),
        runbook_match=data.get("runbook_match"),
        service=data.get("service"),
        severity=data.get("severity"),
        error_summary=data.get("error_summary"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel("aiops-gateway")
    setup_mlflow_tracing("aiops-platform")
    ref_root = shared.config.AGENT_ROOT
    from rag.indexer import active_manifest_path

    if not active_manifest_path().exists():
        import logging

        logging.getLogger("gateway").warning(
            "Runbook index manifest missing — ensure runbook-ingestion service is healthy"
        )
    ensure_tables()
    ensure_eval_tables()
    ensure_governance_tables()
    seed_agent_registry()
    seed_skills_registry()
    yield


app = FastAPI(title="Production AgentOps Platform", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user)
    return TokenResponse(access_token=token, role=user.role, name=user.name)


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return user


@app.patch("/api/auth/profile")
def update_user_profile(body: ProfileUpdateRequest, user: User = Depends(get_current_user)):
    profile = update_profile(user.email, body)
    return profile


@app.post("/api/auth/change-password")
def update_password(body: ChangePasswordRequest, user: User = Depends(get_current_user)):
    change_password(user.email, body)
    return {"ok": True, "message": "Password updated"}


@app.get("/api/admin/overview")
def admin_overview(user: User = Depends(require_admin)):
    stats = get_dashboard_stats()
    opa = get_evaluation_stats()
    hitl = list_hitl_decisions(limit=8)
    return {
        "platform_stats": stats,
        "user_counts": user_counts_by_role(),
        "total_users": sum(user_counts_by_role().values()),
        "opa_stats": opa,
        "recent_hitl": hitl[:8],
        "recent_runs": list_recent_runs(limit=10),
    }


@app.get("/api/admin/users")
def admin_list_users(user: User = Depends(require_admin)):
    return {"users": list_users_public(), "total": len(list_users_public())}


@app.post("/api/admin/users")
def admin_create_user(body: AdminUserCreateRequest, user: User = Depends(require_admin)):
    created = create_user(body)
    return {"user": created}


@app.patch("/api/admin/users/{email}")
def admin_update_user(email: str, body: AdminUserUpdateRequest, user: User = Depends(require_admin)):
    updated = update_user(email, body)
    return {"user": updated}


@app.delete("/api/admin/users/{email}")
def admin_delete_user(email: str, user: User = Depends(require_admin)):
    delete_user(email, actor_email=user.email)
    return {"ok": True}


@app.post("/api/agents/invoke", response_model=AgentResponse)
def invoke_agent(body: AlertRequest, user: User = Depends(require_roles("operator", "admin"))):
    thread_id = body.thread_id or str(uuid.uuid4())
    graph = _graph_for_mode(body.mode, body.domain)
    config = build_invoke_config(f"{body.domain}-{body.mode}-invoke", session_id=thread_id)
    config["metadata"] = {
        **(config.get("metadata") or {}),
        "user": user.email,
        "mode": body.mode,
        "domain": body.domain,
    }
    _persist_run_start(body, thread_id, user.email)
    try:
        result = graph.invoke({"alert": body.model_dump(exclude={"thread_id", "mode"})}, config=config)
    except Exception as exc:
        record_run_finish(thread_id=thread_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    response = _serialize(body.mode, thread_id, result, graph, config, body.domain)
    response.service = body.service
    response.severity = body.severity
    response.error_summary = body.error_summary
    _persist_run_outcome(thread_id, response)
    _notify_hitl_if_needed(body, response)
    lf_handler = (config.get("callbacks") or [None])[0]
    trace_id = getattr(lf_handler, "trace_id", None) if lf_handler else None
    flush_langfuse()
    record_pipeline_scores(
        thread_id,
        mode=body.mode,
        domain=body.domain,
        hitl_required=bool(response.requires_hitl),
        trace_id=trace_id,
    )
    flush_langfuse()
    return response


def _invoke_config_for_thread(mode: str, domain: str, thread_id: str) -> dict:
    """Must match the config used by /api/agents/invoke so checkpoints align."""
    return build_invoke_config(f"{domain}-{mode}-invoke", session_id=thread_id)


def _serialize_from_checkpoint(mode: str, domain: str, thread_id: str, graph, config) -> AgentResponse:
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    result = state.values
    alert = result.get("alert") or {}
    status = "awaiting_hitl" if state.next else "completed"
    return AgentResponse(
        domain=domain,
        mode=mode,
        thread_id=thread_id,
        status=status,
        classification=result.get("classification"),
        recommendation=result.get("recommendation") or result.get("final_response"),
        runbook_id=result.get("runbook_id"),
        requires_hitl=result.get("requires_hitl", False),
        hitl_approved=bool(result.get("hitl_approved")),
        ticket=result.get("ticket"),
        worker_trace=result.get("worker_trace"),
        delegation_events=result.get("delegation_events"),
        mcp_tool_calls=result.get("mcp_tool_calls"),
        route=result.get("route"),
        runbook_chunks=result.get("runbook_chunks"),
        runbook_gap=bool(result.get("runbook_gap")),
        runbook_match=result.get("runbook_match"),
        final_response=result.get("final_response"),
        service=alert.get("service"),
        severity=alert.get("severity"),
        error_summary=alert.get("error_summary"),
    )


def _approve_via_agent(body: ApproveRequest) -> AgentResponse:
    url = f"{shared.config.AGENT_URL}/approve"
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json={"thread_id": body.thread_id, "approved": True})
        r.raise_for_status()
        data = r.json()
    return _agent_response_from_json(body.mode, body.domain, data)


@app.get("/api/agents/state/{thread_id}", response_model=AgentResponse)
def get_agent_state(thread_id: str, user: User = Depends(require_roles("operator", "admin"))):
    """UI runs checkpoint on gateway; alert webhooks use the agent service."""
    graph = get_standalone_graph()
    config = _invoke_config_for_thread("standalone", "sre", thread_id)
    if graph.get_state(config).values:
        return _serialize_from_checkpoint("standalone", "sre", thread_id, graph, config)

    url = f"{shared.config.AGENT_URL}/state/{thread_id}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url)
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Unknown thread_id")
            r.raise_for_status()
            data = r.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent state unavailable: {exc}") from exc
    return _agent_response_from_json("standalone", "sre", data)


@app.post("/api/agents/approve", response_model=AgentResponse)
def approve_agent(body: ApproveRequest, user: User = Depends(require_roles("operator", "admin"))):
    if not body.approved:
        record_hitl_decision(
            thread_id=body.thread_id,
            decision="rejected",
            decided_by=user.email,
            service=body.service,
            severity=body.severity,
            runbook_id=body.runbook_id,
            recommendation=body.recommendation,
            opa_allowed=body.opa_allowed,
            opa_rule=body.opa_rule,
            reason=_build_hitl_reason(decision="rejected", body=body),
        )
        record_run_finish(thread_id=body.thread_id, status="cancelled")
        return AgentResponse(
            domain=body.domain,
            mode=body.mode,
            thread_id=body.thread_id,
            status="cancelled",
            service=body.service,
            severity=body.severity,
            runbook_id=body.runbook_id,
            recommendation=body.recommendation,
            hitl_approved=False,
        )

    graph = _graph_for_mode(body.mode, body.domain)
    config = _invoke_config_for_thread(body.mode, body.domain, body.thread_id)
    checkpoint = graph.get_state(config)

    # Slack/webhook runs live on the agent; platform UI invoke uses gateway memory.
    if not checkpoint.values:
        if body.mode == "standalone" and body.domain == "sre":
            try:
                response = _approve_via_agent(body)
                _persist_run_outcome(body.thread_id, response)
                _record_execute_evaluation(response, user)
                _record_hitl_approval(body, response, user)
                return response
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Agent approve failed: {exc}") from exc
        raise HTTPException(status_code=404, detail="Unknown thread_id — run the agent first")

    if not checkpoint.next:
        response = _serialize_from_checkpoint(body.mode, body.domain, body.thread_id, graph, config)
        _persist_run_outcome(body.thread_id, response)
        _record_hitl_approval(body, response, user)
        return response

    graph.update_state(config, {"hitl_approved": True, "hitl_approver": user.email})
    try:
        result = graph.invoke(None, config=config)
    except Exception as exc:
        record_run_finish(thread_id=body.thread_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    response = _serialize(body.mode, body.thread_id, result, graph, config, body.domain)
    _persist_run_outcome(body.thread_id, response)
    _record_execute_evaluation(response, user)
    _record_hitl_approval(body, response, user)
    lf_handler = (config.get("callbacks") or [None])[0]
    trace_id = getattr(lf_handler, "trace_id", None) if lf_handler else None
    flush_langfuse()
    record_pipeline_scores(
        body.thread_id,
        mode=body.mode,
        domain=body.domain,
        hitl_required=False,
        trace_id=trace_id,
    )
    flush_langfuse()
    return response


@app.get("/api/agents/domains")
def list_domains(user: User = Depends(get_current_user)):
    return {
        "domains": [
            {
                "id": "sre",
                "label": "SRE Incident Response",
                "description": "Production infra — Loki, Prometheus, Chroma runbooks, HITL",
                "recommended_mode": "standalone",
                "modes": ["standalone", "multi", "mcp"],
            },
        ]
    }


@app.get("/api/agents/scenarios")
def list_scenarios(user: User = Depends(get_current_user)):
    return {"scenarios": list_sre_scenarios()}


@app.get("/api/agents/modes")
def list_modes(user: User = Depends(get_current_user)):
    seed_agent_registry()
    modes = [
        {
            "id": "standalone",
            "label": "Standalone Agent",
            "description": "Single LangGraph orchestrator pipeline",
            "agents": list_registry_agents(mode="standalone"),
        },
        {
            "id": "multi",
            "label": "Multi-Agent System",
            "description": "Supervisor delegates to specialist worker agents",
            "agents": list_registry_agents(mode="multi"),
        },
        {
            "id": "mcp",
            "label": "MCP Agent",
            "description": "Tools via hosted MCP HTTP server (Basic Auth)",
            "agents": list_registry_agents(mode="mcp"),
        },
    ]
    return {"modes": modes}


@app.get("/api/agents/registry")
def agents_registry(mode: str | None = None, kind: str | None = None, user: User = Depends(get_current_user)):
    items = list_registry_agents(mode=mode, kind=kind)
    return {
        "agents": items,
        "total": len(items),
        "backend": registry_backend(),
        "registry_url": registry_public_url(),
    }


@app.get("/api/agents/registry/{slug}")
def agents_registry_detail(slug: str, user: User = Depends(get_current_user)):
    agent = get_registry_agent(slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.post("/api/agents/registry")
def agents_registry_create(body: RegisterAgentRequest, user: User = Depends(require_admin)):
    agent = register_agent(
        slug=body.slug,
        name=body.name,
        kind=body.kind,
        mode=body.mode,
        description=body.description,
        tools=body.tools,
        risk_tier=body.risk_tier,
        owner=body.owner,
        status=body.status,
        is_builtin=False,
    )
    return {"agent": agent, "created_by": user.email}


@app.get("/api/skills")
def skills_list(category: str | None = None, user: User = Depends(get_current_user)):
    items = list_skills(category=category)
    return {
        "skills": items,
        "total": len(items),
        "backend": skills_registry_backend(),
        "registry_url": registry_public_url(),
    }


@app.get("/api/skills/guide/mcp-vs-skills")
def skills_mcp_guide(user: User = Depends(get_current_user)):
    return mcp_vs_skills_guide()


@app.get("/api/skills/{slug}")
def skills_detail(slug: str, user: User = Depends(get_current_user)):
    skill = get_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@app.post("/api/skills/{slug}/run")
def skills_run(slug: str, body: SkillRunRequest, user: User = Depends(get_current_user)):
    try:
        result = run_skill_script(slug, body.script, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Skill script timed out") from exc
    return {"run_by": user.email, **result}


@app.get("/api/agents/mcp/config")
def mcp_runtime_config(user: User = Depends(get_current_user)):
    import os

    healthy = False
    try:
        from mcp_server.client import mcp_server_health

        healthy = mcp_server_health().get("status") == "ok"
    except Exception:
        healthy = False

    return {
        "http_url": os.getenv("MCP_HTTP_URL", "http://mcp-server:8081"),
        "auth": "basic",
        "user": os.getenv("MCP_BASIC_USER", "mcp"),
        "http_enabled": os.getenv("MCP_HTTP_ENABLED", "true").lower() == "true",
        "healthy": healthy,
        "tools": ["query_logs", "retrieve_runbooks", "get_metrics", "create_ticket"],
    }


@app.get("/api/mcp/playground/servers")
def mcp_playground_servers(user: User = Depends(get_current_user)):
    return {"servers": list_playground_servers()}


@app.post("/api/mcp/playground/connect")
def mcp_playground_connect(body: McpPlaygroundConnect, user: User = Depends(get_current_user)):
    try:
        return connect_server(
            body.server_id,
            url=body.url,
            username=body.username,
            password=body.password,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:500]) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/mcp/playground/invoke")
def mcp_playground_invoke(body: McpPlaygroundInvoke, user: User = Depends(get_current_user)):
    try:
        return invoke_tool(
            body.server_id,
            body.tool,
            body.payload,
            url=body.url,
            username=body.username,
            password=body.password,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:500]) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/health")
def health():
    return {"status": "ok", "platform": "production-agentops", "version": "2.0.0"}


@app.get("/api/dashboard/stats")
def dashboard_stats(user: User = Depends(get_current_user)):
    return get_dashboard_stats()


@app.post("/api/internal/dashboard/runs")
def internal_dashboard_run(body: DashboardRunEvent):
    if body.event == "start":
        record_run_start(
            thread_id=body.thread_id,
            mode=body.mode,
            domain=body.domain,
            service=body.service,
            severity=body.severity,
            status=body.status,
            runbook_id=body.runbook_id,
            triggered_by=body.triggered_by,
            source=body.source,
            hitl_required=body.hitl_required,
        )
    else:
        record_run_finish(
            thread_id=body.thread_id,
            status=body.status,
            runbook_id=body.runbook_id,
            ticket_id=body.ticket_id,
            hitl_required=body.hitl_required,
            error_message=body.error_message,
        )
    return {"ok": True}


def _ingestion_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {shared.config.INGESTION_API_TOKEN}"}


@app.get("/api/ingest/status")
def ingest_status(user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/status"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_ingestion_headers())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion service unavailable: {exc}") from exc


@app.post("/api/ingest/reindex")
def ingest_reindex(body: IngestReindexRequest, user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/reindex"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=_ingestion_headers(), json=body.model_dump())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion reindex failed: {exc}") from exc


@app.post("/api/ingest/sync-drive")
def ingest_sync_drive(user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/sync-drive"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=_ingestion_headers())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drive sync failed: {exc}") from exc


@app.get("/api/ingest/jobs/{job_id}")
def ingest_job(job_id: str, user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/jobs/{job_id}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_ingestion_headers())
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/ingest/index")
def ingest_index(limit: int = 500, collection: str | None = None, user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/index"
    try:
        with httpx.Client(timeout=20.0) as client:
            params = {"limit": limit}
            if collection:
                params["collection"] = collection
            r = client.get(url, headers=_ingestion_headers(), params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion index browse failed: {exc}") from exc


@app.get("/api/ingest/index/collections")
def ingest_index_collections(user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/index/collections"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_ingestion_headers())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Collections lookup failed: {exc}") from exc


@app.get("/api/ingest/index/chunks/{chunk_id}")
def ingest_index_chunk(chunk_id: str, collection: str | None = None, user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/index/chunks/{chunk_id}"
    try:
        with httpx.Client(timeout=20.0) as client:
            params = {"collection": collection} if collection else None
            r = client.get(url, headers=_ingestion_headers(), params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chunk lookup failed: {exc}") from exc


class IngestIndexQueryRequest(BaseModel):
    query: str
    n_results: int = 5
    collection: str | None = None
    service: str | None = None
    severity: str | None = None
    runbook_id: str | None = None


class OpaEvaluateRequest(BaseModel):
    service: str
    severity: str
    recommendation: str
    thread_id: str | None = None
    source: str = "ui_preview"
    record: bool = True


class OpaPolicySaveRequest(BaseModel):
    rego: str
    note: str | None = None


def _build_hitl_reason(
    *,
    decision: str,
    body: ApproveRequest,
    response: AgentResponse | None = None,
) -> str:
    if body.reason and body.reason.strip():
        return body.reason.strip()[:2000]
    service = body.service or (response.service if response else None) or "service"
    severity = body.severity or (response.severity if response else None) or "P1"
    runbook = body.runbook_id or (response.runbook_id if response else None) or "runbook"
    rec = (body.recommendation or (response.recommendation if response else None) or "").strip()
    opa_rule = body.opa_rule or "policy"
    if decision == "approved":
        ticket_id = _ticket_id_from_response(response) if response else None
        parts = [
            f"Approved: operator accepted {severity} remediation for {service}.",
            f"OPA allowed ({opa_rule}); runbook {runbook}.",
        ]
        if rec:
            parts.append(f"Action: {rec[:240]}")
        if ticket_id:
            parts.append(f"Ticket {ticket_id} created.")
        return " ".join(parts)
    parts = [
        f"Rejected: operator declined remediation for {service} ({severity}).",
        "No ticket created; pipeline stopped before execute.",
    ]
    if rec:
        parts.append(f"Declined action: {rec[:240]}")
    return " ".join(parts)


def _record_hitl_approval(body: ApproveRequest, response: AgentResponse, user: User) -> None:
    opa = last_opa_for_thread(body.thread_id)
    record_hitl_decision(
        thread_id=body.thread_id,
        decision="approved",
        decided_by=user.email,
        service=response.service or body.service,
        severity=response.severity or body.severity,
        runbook_id=response.runbook_id or body.runbook_id,
        recommendation=response.recommendation or body.recommendation,
        opa_allowed=opa.get("allowed") if opa else body.opa_allowed,
        opa_rule=opa.get("matched_rule") if opa else body.opa_rule,
        ticket_id=_ticket_id_from_response(response),
        reason=_build_hitl_reason(decision="approved", body=body, response=response),
    )


def last_opa_for_thread(thread_id: str) -> dict[str, Any] | None:
    rows = list_evaluations(limit=20, verdict=None)
    for row in rows:
        if row.get("thread_id") == thread_id and row.get("source") == "hitl_preview":
            return row
    return None


def _record_execute_evaluation(response: AgentResponse, user: User) -> None:
    rec = response.recommendation or ""
    if not rec:
        return
    ticket = response.ticket or {}
    if ticket.get("status") == "blocked_by_policy":
        allowed, reason = False, ticket.get("message", "policy_deny")
    elif ticket.get("status") in ("pending_hitl", "error"):
        return
    else:
        allowed, reason = True, "policy_allow"
    result = build_evaluation_result(
        service=response.service or "",
        recommendation=rec,
        severity=response.severity or "P3",
        allowed=allowed,
        reason=reason,
    )
    record_evaluation(
        result=result,
        evaluated_by=user.email,
        thread_id=response.thread_id,
        source="execute",
    )


@app.post("/api/ingest/index/query")
def ingest_index_query(body: IngestIndexQueryRequest, user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.INGESTION_URL.rstrip('/')}/v1/ingest/index/query"
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(url, headers=_ingestion_headers(), json=body.model_dump())
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Semantic query failed: {exc}") from exc


@app.post("/api/guardrails/opa/evaluate")
def evaluate_opa_policy(body: OpaEvaluateRequest, user: User = Depends(get_current_user)):
    result = build_evaluation_result(
        service=body.service,
        recommendation=body.recommendation,
        severity=body.severity,
    )
    if body.record:
        audit = record_evaluation(
            result=result,
            evaluated_by=user.email,
            thread_id=body.thread_id,
            source=body.source,
        )
        result["audit_id"] = audit["id"]
    return result


@app.get("/api/guardrails/opa/evaluations")
def opa_evaluations(
    limit: int = 100,
    verdict: str | None = None,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    return {"evaluations": list_evaluations(limit=min(limit, 500), verdict=verdict)}


@app.get("/api/guardrails/opa/stats")
def opa_stats(user: User = Depends(get_current_user)):
    rego = read_policy_rego()
    stats = get_evaluation_stats()
    stats.update(
        {
            "package": "agentops",
            "endpoint": f"{os.getenv('OPA_URL', 'http://opa:8181')}/v1/data/agentops/allow",
            "destructive_keywords": parse_destructive_keywords(rego),
            "rules": [
                {"id": "allow_non_destructive", "label": "Non-destructive recommendation", "effect": "allow"},
                {"id": "allow_p1_destructive", "label": "Destructive action + P1 severity", "effect": "allow"},
                {"id": "deny_destructive_not_p1", "label": "Destructive action on P2/P3", "effect": "deny"},
            ],
        }
    )
    return stats


@app.get("/api/guardrails/opa/policy")
def opa_policy_summary(user: User = Depends(get_current_user)):
    rego = read_policy_rego()
    return {
        "package": "agentops",
        "endpoint": f"{os.getenv('OPA_URL', 'http://opa:8181')}/v1/data/agentops/allow",
        "rego": rego,
        "path": str(os.getenv("OPA_POLICY_PATH", "deploy/config/opa/policy.rego")),
        "destructive_keywords": parse_destructive_keywords(rego),
        "revisions": list_policy_revisions(limit=5),
    }


@app.put("/api/guardrails/opa/policy")
def opa_policy_save(body: OpaPolicySaveRequest, user: User = Depends(require_roles("operator", "admin"))):
    if not body.rego.strip():
        raise HTTPException(status_code=400, detail="Policy body is empty")
    try:
        saved = save_policy_rego(rego=body.rego, saved_by=user.email, note=body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return saved


@app.get("/api/guardrails/opa/revisions")
def opa_policy_revisions(limit: int = 20, user: User = Depends(require_roles("operator", "admin", "viewer"))):
    return {"revisions": list_policy_revisions(limit=min(limit, 50))}


@app.post("/api/runbooks/draft")
def draft_runbook(body: RunbookDraftRequest, user: User = Depends(require_roles("operator", "admin"))):
    from shared.runbook_author import draft_runbook_markdown, persist_runbook

    drafted = draft_runbook_markdown(
        service=body.service,
        severity=body.severity,
        error_summary=body.error_summary,
        log_snippet=body.log_snippet,
        recommendation=body.recommendation,
    )
    published = None
    if body.persist:
        try:
            published = persist_runbook(
                runbook_id=drafted["runbook_id"],
                markdown=drafted["markdown"],
                triggered_by=user.email,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Ingestion publish failed: {exc}") from exc
    return {**drafted, "persisted": bool(published), "ingest": published}


@app.post("/api/runbooks/gap/ticket")
def gap_ticket(body: GapTicketRequest, user: User = Depends(require_roles("operator", "admin"))):
    from agent.tools.ticket_create import create_ticket

    rec = body.recommendation or f"Unmatched runbook for {body.service}: {body.error_summary}"
    return create_ticket(body.service, body.severity, rec, "none", approved_by=user.email)


@app.get("/api/tickets")
def list_tickets(user: User = Depends(require_roles("operator", "admin"))):
    url = f"{shared.config.TICKET_API_URL.rstrip('/')}/tickets"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
            r.raise_for_status()
            return {"tickets": r.json()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ticket API unavailable: {exc}") from exc


@app.get("/api/config/links")
def observability_links(user: User = Depends(get_current_user)):
    return {
        "langfuse": os.getenv("LANGFUSE_PUBLIC_URL", "http://localhost:3000"),
        "mlflow": os.getenv("MLFLOW_PUBLIC_URL", "http://localhost:5001"),
        "grafana": os.getenv("GRAFANA_PUBLIC_URL", "http://localhost:3001"),
        "prometheus": os.getenv("VM_PUBLIC_URL", os.getenv("PROMETHEUS_PUBLIC_URL", "http://localhost:8428")),
        "opa": os.getenv("OPENFGA_PUBLIC_URL", os.getenv("OPA_PUBLIC_URL", "http://localhost:8085")),
        "kibana": os.getenv("KIBANA_PUBLIC_URL", "http://localhost:5601"),
        "weaviate": os.getenv("WEAVIATE_PUBLIC_URL", "http://localhost:8088"),
        "vector": os.getenv("WEAVIATE_PUBLIC_URL", os.getenv("OPENSEARCH_DASHBOARDS_PUBLIC_URL", "http://localhost:8088")),
        "phoenix": os.getenv("PHOENIX_PUBLIC_URL", "http://localhost:6006"),
        "opensearch": os.getenv("OPENSEARCH_PUBLIC_URL", "http://localhost:9201"),
        "opensearch_dashboards": os.getenv("OPENSEARCH_DASHBOARDS_PUBLIC_URL", "http://localhost:5602"),
        "mimir": os.getenv("MIMIR_PUBLIC_URL", "http://localhost:9009"),
        "tempo": os.getenv("TEMPO_PUBLIC_URL", "http://localhost:3200"),
        "elasticsearch": os.getenv("ELASTICSEARCH_PUBLIC_URL", "http://localhost:9200"),
    }


@app.get("/api/observability/traces/{session_id}")
def get_langfuse_trace(session_id: str, user: User = Depends(require_roles("operator", "admin", "viewer"))):
    """Hierarchical Langfuse trace for platform UI (orchestrator → nodes → LLM/tools)."""
    return fetch_trace_by_session(session_id)


@app.get("/api/observability/alerts/catalog")
def alerts_catalog(user: User = Depends(require_roles("operator", "admin", "viewer"))):
    """Alert types, live Prometheus values, log previews."""
    return get_alert_catalog()


@app.post("/api/observability/alerts/simulate")
def alerts_simulate(body: AlertSimulateRequest, user: User = Depends(require_roles("operator", "admin"))):
    """Build step-by-step payloads for metrics → Prometheus → Alertmanager → agent."""
    try:
        return simulate_alert_flow(
            alert_id=body.alert_id,
            custom_alert=body.custom_alert,
            invoke_agent=body.invoke_agent,
            design_id=body.design_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/simulation/hitl/history")
def hitl_history(decision: str | None = None, user: User = Depends(require_roles("operator", "admin", "viewer"))):
    """All HITL approve/reject decisions with operator attribution."""
    items = list_hitl_decisions(limit=100, decision=decision if decision in ("approved", "rejected") else None)
    return {"decisions": items, "total": len(items)}


@app.get("/api/observability/langfuse/dashboard")
def get_langfuse_dashboard(
    design_id: str | None = None,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    """Aggregated analytics — Langfuse for D1, Phoenix/MLflow messages for D2/D3."""
    return fetch_langfuse_dashboard(design_id=design_id)


@app.get("/api/evaluation/dashboard")
def evaluation_dashboard(
    design_id: str | None = None,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    """Golden-set eval gate status for the selected design's eval tool."""
    return get_eval_dashboard(design_id=design_id)


@app.post("/api/evaluation/run")
def evaluation_run(body: EvalRunRequest = EvalRunRequest(), user: User = Depends(require_roles("operator", "admin"))):
    """Run golden_alerts.json and publish scores to Langfuse (D1), Phoenix (D2), or MLflow (D3)."""
    try:
        return run_eval_suite(triggered_by=user.email, source="platform", design_id=body.design_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/governance/overview")
def api_governance_overview(user: User = Depends(require_roles("operator", "admin", "viewer"))):
    return governance_overview()


@app.get("/api/governance/pipelines")
def api_governance_pipelines(
    limit: int = 30,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    return {"runs": list_pipeline_runs(limit=limit), "github": github_config()}


@app.get("/api/governance/promotions")
def api_governance_promotions(
    limit: int = 20,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    return {"promotions": list_promotions(limit=limit)}


@app.post("/api/governance/promotions")
def api_governance_request_promotion(
    body: PromotionRequest,
    user: User = Depends(require_roles("operator", "admin")),
):
    return request_promotion(
        environment=body.environment,
        requested_by=user.email,
        reason=body.reason,
        sha=body.sha,
        eval_run_id=body.eval_run_id,
    )


@app.post("/api/governance/promotions/{promotion_id}/decide")
def api_governance_decide_promotion(
    promotion_id: str,
    body: PromotionDecideRequest,
    user: User = Depends(require_roles("operator", "admin")),
):
    try:
        return decide_promotion(
            promotion_id=promotion_id,
            approved=body.approved,
            decided_by=user.email,
            note=body.note,
            actor_role=user.role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/governance/audit")
def api_governance_audit(
    limit: int = 40,
    user: User = Depends(require_roles("operator", "admin", "viewer")),
):
    return {"events": list_audit(limit=limit)}


@app.get("/api/governance/github")
def api_governance_github(user: User = Depends(require_roles("operator", "admin", "viewer"))):
    return github_config()


@app.post("/api/governance/github/webhook")
def api_governance_github_webhook(
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
    x_governance_token: str | None = Header(default=None),
):
    """Optional GitHub Actions callback. Token required only when GOVERNANCE_WEBHOOK_TOKEN is set."""
    expected = os.getenv("GOVERNANCE_WEBHOOK_TOKEN", "")
    if expected:
        bearer = (authorization or "").removeprefix("Bearer ").strip()
        token = x_governance_token or bearer
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid governance webhook token")
    sender = ((payload.get("sender") or {}).get("login")) or "github"
    return ingest_github_event(payload, triggered_by=sender)


@app.get("/")
def ui_index():
    return FileResponse(
        UI_DIR / "index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")
