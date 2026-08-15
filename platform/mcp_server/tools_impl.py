"""Agent-side MCP tool access — HTTP to hosted server or in-process fallback."""

from __future__ import annotations

import os
from typing import Any

from mcp_server.tools_internal import (
    run_create_ticket,
    run_get_metrics,
    run_query_logs,
    run_retrieve_runbooks,
)

def _mcp_http_enabled() -> bool:
    return os.getenv("MCP_HTTP_ENABLED", "true").lower() == "true"


def _record_call(calls: list[dict], tool: str, payload: dict, result: Any, *, transport: str) -> None:
    entry = {
        "tool": tool,
        "transport": transport,
        "input": {k: v for k, v in payload.items()},
        "ok": True,
    }
    if isinstance(result, dict):
        if "chunks" in result:
            entry["summary"] = f"{len(result.get('chunks') or [])} runbook chunks"
        elif "ticket_id" in result:
            entry["summary"] = result.get("ticket_id")
        elif "cpu_percent" in result:
            entry["summary"] = f"cpu={result.get('cpu_percent')}% p95={result.get('p95_latency_ms')}ms"
        else:
            entry["summary"] = "ok"
    elif isinstance(result, list):
        entry["summary"] = f"{len(result)} log lines"
    else:
        entry["summary"] = "ok"
    calls.append(entry)


def mcp_query_logs(service: str, error_summary: str, limit: int = 5, *, calls: list[dict] | None = None) -> list[dict]:
    payload = {"service": service, "error_summary": error_summary, "limit": limit}
    if _mcp_http_enabled():
        from mcp_server.client import mcp_http_call

        result = mcp_http_call("query_logs", payload)
    else:
        result = run_query_logs(service, error_summary, limit)
    if calls is not None:
        _record_call(calls, "query_logs", payload, result, transport="mcp_http" if _mcp_http_enabled() else "in_process")
    return result if isinstance(result, list) else result.get("logs", [])


def mcp_retrieve_runbooks(query: str, service: str = "", top_k: int = 3, *, calls: list[dict] | None = None) -> dict:
    payload = {"query": query, "service": service, "top_k": top_k}
    if _mcp_http_enabled():
        from mcp_server.client import mcp_http_call

        result = mcp_http_call("retrieve_runbooks", payload)
    else:
        result = run_retrieve_runbooks(query, service, top_k)
    if calls is not None:
        _record_call(calls, "retrieve_runbooks", payload, result, transport="mcp_http" if _mcp_http_enabled() else "in_process")
    return result


def mcp_create_ticket(service: str, severity: str, recommendation: str, runbook_id: str, *, calls: list[dict] | None = None) -> dict:
    payload = {
        "service": service,
        "severity": severity,
        "recommendation": recommendation,
        "runbook_id": runbook_id,
    }
    if _mcp_http_enabled():
        from mcp_server.client import mcp_http_call

        result = mcp_http_call("create_ticket", payload)
    else:
        result = run_create_ticket(service, severity, recommendation, runbook_id)
    if calls is not None:
        _record_call(calls, "create_ticket", payload, result, transport="mcp_http" if _mcp_http_enabled() else "in_process")
    return result


def mcp_get_metrics(service: str, *, calls: list[dict] | None = None) -> dict:
    payload = {"service": service}
    if _mcp_http_enabled():
        from mcp_server.client import mcp_http_call

        result = mcp_http_call("get_metrics", payload)
    else:
        result = run_get_metrics(service)
    if calls is not None:
        _record_call(calls, "get_metrics", payload, result, transport="mcp_http" if _mcp_http_enabled() else "in_process")
    return result
