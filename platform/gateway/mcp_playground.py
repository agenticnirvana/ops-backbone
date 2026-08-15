"""MCP Playground — proxy connect, list tools, and invoke (inspector-style)."""

from __future__ import annotations

import os
from typing import Any

import httpx

MCP_HTTP_URL = os.getenv("MCP_HTTP_URL", "http://mcp-server:8081").rstrip("/")
MCP_POLICY_HTTP_URL = os.getenv("MCP_POLICY_HTTP_URL", "http://mcp-policy-server:8082").rstrip("/")
MCP_RAG_HTTP_URL = os.getenv("MCP_RAG_HTTP_URL", "http://mcp-rag-server:8083").rstrip("/")
MCP_BASIC_USER = os.getenv("MCP_BASIC_USER", "mcp")
MCP_BASIC_PASSWORD = os.getenv("MCP_BASIC_PASSWORD", "mcp-secret")

BUILTIN_SERVERS: dict[str, dict[str, Any]] = {
    "ops-local": {
        "name": "Ops MCP Server",
        "description": "Full observability + tickets · Loki, Chroma, Prometheus, ticket-api",
        "url_env": "MCP_HTTP_URL",
        "default_url": MCP_HTTP_URL,
        "port": 8081,
    },
    "policy-local": {
        "name": "Policy & Guardrails MCP",
        "description": "OPA preview · list rules · HITL gate simulation (no side effects)",
        "url_env": "MCP_POLICY_HTTP_URL",
        "default_url": MCP_POLICY_HTTP_URL,
        "port": 8082,
    },
    "rag-local": {
        "name": "Runbook Knowledge MCP",
        "description": "RAG retrieval · runbook catalog · fetch by ID (read-only knowledge)",
        "url_env": "MCP_RAG_HTTP_URL",
        "default_url": MCP_RAG_HTTP_URL,
        "port": 8083,
    },
}

TOOL_SAMPLES: dict[str, dict[str, Any]] = {
    "query_logs": {
        "service": "checkout-service",
        "error_summary": "Redis connection pool exhausted",
        "limit": 5,
    },
    "retrieve_runbooks": {
        "query": "checkout redis pool timeout",
        "service": "checkout-service",
        "top_k": 3,
    },
    "get_metrics": {"service": "checkout-service"},
    "create_ticket": {
        "service": "checkout-service",
        "severity": "P1",
        "recommendation": "Increase REDIS_MAX_CONNECTIONS from 50 to 150",
        "runbook_id": "checkout-redis-pool",
    },
    "check_opa_policy": {
        "service": "checkout-service",
        "severity": "P1",
        "recommendation": "Restart checkout-service pods to clear Redis pool",
    },
    "list_policy_rules": {},
    "preview_hitl_gate": {
        "service": "checkout-service",
        "severity": "P2",
        "recommendation": "Scale Redis connections and monitor checkout error rate",
    },
    "list_runbooks": {},
    "get_runbook_by_id": {"runbook_id": "checkout-redis-pool", "max_chars": 800},
}


def _server_url(server_id: str, url: str | None) -> str:
    meta = BUILTIN_SERVERS.get(server_id)
    if meta:
        return (url or meta["default_url"]).rstrip("/")
    if not url:
        raise ValueError("URL required for custom MCP servers")
    return url.rstrip("/")


def _resolve_server(server_id: str, url: str | None, username: str | None, password: str | None) -> tuple[str, str, str]:
    if server_id in BUILTIN_SERVERS:
        return (
            _server_url(server_id, url),
            username or MCP_BASIC_USER,
            password or MCP_BASIC_PASSWORD,
        )
    if not url:
        raise ValueError("URL required for custom MCP servers")
    if not username or not password:
        raise ValueError("Username and password required")
    return url.rstrip("/"), username, password


def _probe_health(base: str, user: str, passwd: str) -> bool:
    try:
        with httpx.Client(timeout=4.0) as client:
            r = client.get(f"{base}/health", auth=(user, passwd))
            return r.status_code < 400 and r.json().get("status") == "ok"
    except Exception:
        return False


def list_playground_servers() -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []
    for server_id, meta in BUILTIN_SERVERS.items():
        base = meta["default_url"]
        servers.append(
            {
                "id": server_id,
                "name": meta["name"],
                "description": meta["description"],
                "url": base,
                "auth": "basic",
                "transport": "http+json",
                "builtin": True,
                "healthy": _probe_health(base, MCP_BASIC_USER, MCP_BASIC_PASSWORD),
                "default_user": MCP_BASIC_USER,
                "port": meta["port"],
            }
        )
    return servers


def connect_server(
    server_id: str,
    *,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    base, user, passwd = _resolve_server(server_id, url, username, password)
    with httpx.Client(timeout=15.0) as client:
        health_r = client.get(f"{base}/health", auth=(user, passwd))
        health_r.raise_for_status()
        health = health_r.json()
        tools_r = client.get(f"{base}/tools", auth=(user, passwd))
        tools_r.raise_for_status()
        tools_payload = tools_r.json()

    tools = tools_payload.get("tools") or []
    for tool in tools:
        name = tool.get("name")
        if name and name in TOOL_SAMPLES:
            tool["sample_input"] = TOOL_SAMPLES[name]

    meta = BUILTIN_SERVERS.get(server_id, {})
    return {
        "connected": True,
        "server_id": server_id,
        "server_name": meta.get("name", server_id),
        "url": base,
        "health": health,
        "tools": tools,
        "transport": tools_payload.get("transport", "http+json"),
        "auth": tools_payload.get("auth", "basic"),
    }


def invoke_tool(
    server_id: str,
    tool: str,
    payload: dict[str, Any],
    *,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    base, user, passwd = _resolve_server(server_id, url, username, password)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{base}/tools/{tool}", json=payload, auth=(user, passwd))
        response.raise_for_status()
        result = response.json()
    return {
        "ok": True,
        "tool": tool,
        "server_id": server_id,
        "input": payload,
        "result": result,
        "transport": "mcp_http",
    }
