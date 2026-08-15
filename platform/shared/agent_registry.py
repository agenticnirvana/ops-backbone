"""Agent registry — backed by OSS agentregistry (with local fallback for tests)."""

from __future__ import annotations

import os
from typing import Any

from shared import agentregistry_client as ar

LABEL_PREFIX = "design1.io/"
DEFAULT_NAMESPACE = os.getenv("AGENTREGISTRY_NAMESPACE", "design1")
MCP_HOST_URLS: dict[str, str] = {
    "mcp-ops-server": os.getenv("MCP_HTTP_URL", "http://mcp-server:8081"),
    "mcp-policy-server": os.getenv("MCP_POLICY_HTTP_URL", "http://mcp-policy-server:8082"),
    "mcp-rag-server": os.getenv("MCP_RAG_HTTP_URL", "http://mcp-rag-server:8083"),
}
MCP_REMOTE_URL = MCP_HOST_URLS["mcp-ops-server"]

DEFAULT_AGENTS: list[dict[str, Any]] = [
    {
        "slug": "standalone-orchestrator",
        "name": "SRE Standalone Orchestrator",
        "kind": "orchestrator",
        "mode": "standalone",
        "description": "Single LangGraph pipeline — classify, RAG, logs, metrics, recommend, HITL, execute.",
        "tools": "runbook_rag, log_query, metrics_query, policy_check, ticket_create",
        "risk_tier": "medium",
        "owner": "platform-team",
        "status": "active",
    },
    {
        "slug": "sre-supervisor",
        "name": "SRE Supervisor Orchestrator",
        "kind": "orchestrator",
        "mode": "multi",
        "description": "LangGraph supervisor that delegates alert triage to specialist worker agents.",
        "tools": "routing, delegation",
        "risk_tier": "medium",
        "owner": "platform-team",
        "status": "active",
    },
    {
        "slug": "triage-worker",
        "name": "Triage Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Classifies incident severity and sets HITL requirements.",
        "tools": "llm_classify",
        "risk_tier": "low",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "runbook-worker",
        "name": "Runbook Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Retrieves matching runbooks from Chroma RAG.",
        "tools": "retrieve_runbooks",
        "risk_tier": "low",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "logs-worker",
        "name": "Logs Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Queries Loki for error patterns related to the alert.",
        "tools": "query_logs",
        "risk_tier": "low",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "metrics-worker",
        "name": "Metrics Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Queries Prometheus for CPU, latency, and error-rate anomalies.",
        "tools": "get_metrics",
        "risk_tier": "low",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "remediation-worker",
        "name": "Remediation Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Synthesizes runbook + observability context into actionable recommendations.",
        "tools": "llm_recommend",
        "risk_tier": "high",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "incident-worker",
        "name": "Incident Worker",
        "kind": "worker",
        "mode": "multi",
        "description": "Creates remediation tickets after HITL approval.",
        "tools": "create_ticket",
        "risk_tier": "medium",
        "owner": "sre-oncall",
        "status": "active",
    },
    {
        "slug": "mcp-ops-server",
        "name": "Ops MCP Server",
        "kind": "mcp_host",
        "mode": "mcp",
        "description": "FastAPI-hosted MCP tool server with HTTP Basic Auth — logs, runbooks, metrics, tickets.",
        "tools": "query_logs, retrieve_runbooks, get_metrics, create_ticket",
        "risk_tier": "medium",
        "owner": "platform-team",
        "status": "active",
    },
    {
        "slug": "mcp-policy-server",
        "name": "Policy & Guardrails MCP Server",
        "kind": "mcp_host",
        "mode": "mcp",
        "description": "OPA policy preview, rule catalog, and HITL gate simulation — read-only guardrails exploration.",
        "tools": "check_opa_policy, list_policy_rules, preview_hitl_gate",
        "risk_tier": "low",
        "owner": "platform-team",
        "status": "active",
    },
    {
        "slug": "mcp-rag-server",
        "name": "Runbook Knowledge MCP Server",
        "kind": "mcp_host",
        "mode": "mcp",
        "description": "Chroma RAG retrieval plus runbook catalog tools — knowledge-only MCP split for exploration.",
        "tools": "retrieve_runbooks, list_runbooks, get_runbook_by_id",
        "risk_tier": "low",
        "owner": "platform-team",
        "status": "active",
    },
    {
        "slug": "mcp-agent-runner",
        "name": "MCP Agent Runner",
        "kind": "orchestrator",
        "mode": "mcp",
        "description": "LangGraph agent that calls hosted MCP tools over HTTP instead of in-process imports.",
        "tools": "mcp_http_client",
        "risk_tier": "medium",
        "owner": "platform-team",
        "status": "active",
    },
]

_local_catalog: dict[str, dict[str, Any]] = {}


def registry_backend() -> str:
    return "agentregistry" if _use_agentregistry() else "local-fallback"


def registry_public_url() -> str:
    return os.getenv("AGENTREGISTRY_PUBLIC_URL", "http://localhost:12121")


def _use_agentregistry() -> bool:
    if not ar.AGENTREGISTRY_ENABLED:
        return False
    return ar.ping()


def _label(labels: dict[str, str] | None, key: str, default: str = "") -> str:
    if not labels:
        return default
    return labels.get(f"{LABEL_PREFIX}{key}", labels.get(key, default))


def _annotation(annotations: dict[str, str] | None, key: str, default: str = "") -> str:
    if not annotations:
        return default
    return annotations.get(f"{LABEL_PREFIX}{key}", annotations.get(key, default))


def _tools_list(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _catalog_item_to_dict(item: dict[str, Any]) -> dict[str, Any]:
    tools_raw = item.get("tools", "")
    tools = tools_raw if isinstance(tools_raw, list) else _tools_list(tools_raw)
    return {
        "slug": item["slug"],
        "name": item["name"],
        "kind": item["kind"],
        "mode": item["mode"],
        "description": item.get("description", ""),
        "tools": tools,
        "risk_tier": item.get("risk_tier", "medium"),
        "owner": item.get("owner", "platform-team"),
        "status": item.get("status", "active"),
        "is_builtin": item.get("is_builtin", True),
        "updated_at": item.get("updated_at"),
        "registry": "local-fallback",
    }


def _agentresource_to_dict(resource: dict[str, Any], *, kind_override: str | None = None) -> dict[str, Any]:
    meta = resource.get("metadata") or {}
    spec = resource.get("spec") or {}
    labels = meta.get("labels") or {}
    annotations = meta.get("annotations") or {}
    slug = meta.get("name") or ""
    tools_raw = _annotation(annotations, "tools") or _label(labels, "tools", "")
    return {
        "slug": slug,
        "name": spec.get("title") or slug.replace("-", " ").title(),
        "kind": kind_override or _label(labels, "kind", "orchestrator"),
        "mode": _label(labels, "mode", "standalone"),
        "description": spec.get("description") or "",
        "tools": _tools_list(tools_raw),
        "risk_tier": _label(labels, "risk-tier", "medium"),
        "owner": _label(labels, "owner", "platform-team"),
        "status": _label(labels, "status", "active"),
        "is_builtin": _label(labels, "builtin", "false") == "true",
        "updated_at": meta.get("updatedAt"),
        "registry": "agentregistry",
        "namespace": meta.get("namespace") or DEFAULT_NAMESPACE,
        "tag": meta.get("tag") or "latest",
    }


def _build_labels(item: dict[str, Any]) -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}kind": item["kind"],
        f"{LABEL_PREFIX}mode": item["mode"],
        f"{LABEL_PREFIX}risk-tier": item.get("risk_tier", "medium"),
        f"{LABEL_PREFIX}owner": item.get("owner", "platform-team").replace(" ", "-"),
        f"{LABEL_PREFIX}status": item.get("status", "active"),
        f"{LABEL_PREFIX}builtin": "true" if item.get("is_builtin", True) else "false",
    }


def _build_annotations(item: dict[str, Any]) -> dict[str, str]:
    tools = item.get("tools", "")
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    return {f"{LABEL_PREFIX}tools": tools_str}


def _yaml_map_block(key: str, values: dict[str, str]) -> str:
    lines = [f"  {key}:"]
    for map_key, value in sorted(values.items()):
        safe = str(value).replace('"', '\\"')
        lines.append(f'    {map_key}: "{safe}"')
    return "\n".join(lines)


def _item_to_yaml(item: dict[str, Any], *, namespace: str = DEFAULT_NAMESPACE) -> str:
    labels_yaml = _yaml_map_block("labels", _build_labels(item))
    annotations_yaml = _yaml_map_block("annotations", _build_annotations(item))
    desc = (item.get("description") or "").replace('"', '\\"')
    title = item["name"].replace('"', '\\"')

    if item["kind"] == "mcp_host":
        remote_url = MCP_HOST_URLS.get(item["slug"], MCP_REMOTE_URL)
        return f"""apiVersion: ar.dev/v1alpha1
kind: MCPServer
metadata:
  name: {item["slug"]}
  namespace: {namespace}
  tag: latest
{labels_yaml}
{annotations_yaml}
spec:
  title: "{title}"
  description: "{desc}"
  remote:
    type: streamable-http
    url: {remote_url}
"""

    mcp_refs = ""
    if item["mode"] == "mcp" and item["slug"] == "mcp-agent-runner":
        mcp_refs = """
  mcpServers:
    - kind: MCPServer
      name: mcp-ops-server
      tag: latest"""

    return f"""apiVersion: ar.dev/v1alpha1
kind: Agent
metadata:
  name: {item["slug"]}
  namespace: {namespace}
  tag: latest
{labels_yaml}
{annotations_yaml}
spec:
  title: "{title}"
  description: "{desc}"{mcp_refs}
"""


def build_catalog_yaml(*, namespace: str = DEFAULT_NAMESPACE) -> str:
    # MCP host must be applied before agents that reference it.
    ordered = sorted(DEFAULT_AGENTS, key=lambda item: (0 if item["kind"] == "mcp_host" else 1, item["slug"]))
    docs = [_item_to_yaml(item, namespace=namespace) for item in ordered]
    return "---\n".join(docs) + "\n"


def _fetch_from_agentregistry() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for resource in ar.list_agents():
        items.append(_agentresource_to_dict(resource))
    for resource in ar.list_mcp_servers():
        items.append(_agentresource_to_dict(resource, kind_override="mcp_host"))
    items.sort(key=lambda a: (a["mode"], a["kind"], a["name"]))
    return items


def seed_agent_registry() -> None:
    if not _use_agentregistry():
        for item in DEFAULT_AGENTS:
            slug = item["slug"]
            if slug not in _local_catalog:
                _local_catalog[slug] = _catalog_item_to_dict({**item, "is_builtin": True})
        return

    try:
        existing = {a["slug"] for a in _fetch_from_agentregistry()}
    except Exception:
        existing = set()
    missing = [item for item in DEFAULT_AGENTS if item["slug"] not in existing]
    if not missing:
        return
    ar.apply_yaml(build_catalog_yaml())


def list_registry_agents(*, mode: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    seed_agent_registry()

    if not _use_agentregistry():
        items = [_catalog_item_to_dict(v) for v in _local_catalog.values()]
        if not items:
            items = [_catalog_item_to_dict({**item, "is_builtin": True}) for item in DEFAULT_AGENTS]
    else:
        items = _fetch_from_agentregistry()

    if mode:
        items = [a for a in items if a["mode"] == mode]
    if kind:
        items = [a for a in items if a["kind"] == kind]
    return items


def get_registry_agent(slug: str) -> dict[str, Any] | None:
    seed_agent_registry()
    if not _use_agentregistry():
        item = _local_catalog.get(slug)
        if item:
            return item
        for default in DEFAULT_AGENTS:
            if default["slug"] == slug:
                return _catalog_item_to_dict({**default, "is_builtin": True})
        return None

    agent = ar.get_agent(slug)
    if agent:
        return _agentresource_to_dict(agent)
    mcp = ar.get_mcp_server(slug)
    if mcp:
        return _agentresource_to_dict(mcp, kind_override="mcp_host")
    return None


def register_agent(
    *,
    slug: str,
    name: str,
    kind: str,
    mode: str,
    description: str = "",
    tools: str | list[str] = "",
    risk_tier: str = "medium",
    owner: str = "platform-team",
    status: str = "active",
    is_builtin: bool = False,
) -> dict[str, Any]:
    """Register or update an agent in agentregistry (or local fallback)."""
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    item = {
        "slug": slug,
        "name": name,
        "kind": kind,
        "mode": mode,
        "description": description,
        "tools": tools_str,
        "risk_tier": risk_tier,
        "owner": owner,
        "status": status,
        "is_builtin": is_builtin,
    }

    if not _use_agentregistry():
        _local_catalog[slug] = _catalog_item_to_dict(item)
        return _local_catalog[slug]

    ar.apply_yaml(_item_to_yaml(item))
    registered = get_registry_agent(slug)
    if registered:
        return registered
    return _catalog_item_to_dict(item)
