"""HTTP MCP tool server with Basic Auth and /health for deploy verify scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM_ROOT))

from mcp_server.http_auth import require_mcp_auth
from mcp_server.tools_internal import (
    run_create_ticket,
    run_get_metrics,
    run_query_logs,
    run_retrieve_runbooks,
)

MCP_BASIC_USER = os.getenv("MCP_BASIC_USER", "mcp")
MCP_BASIC_PASSWORD = os.getenv("MCP_BASIC_PASSWORD", "mcp-secret")

app = FastAPI(title="Ops MCP Server", version="1.1.0")


@app.get("/health")
def health(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "status": "ok",
        "service": "mcp-server",
        "phase": 2,
        "auth": "basic",
        "tools": ["query_logs", "retrieve_runbooks", "create_ticket", "get_metrics"],
    }


@app.get("/tools")
def list_tools(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "tools": [
            {"name": "query_logs", "description": "Query Loki error logs for a service"},
            {"name": "retrieve_runbooks", "description": "Chroma RAG runbook lookup"},
            {"name": "create_ticket", "description": "Create incident ticket after HITL"},
            {"name": "get_metrics", "description": "Prometheus CPU/latency/error metrics"},
        ],
        "transport": "http+json",
        "auth": "basic",
    }


@app.post("/tools/{name}")
def call_tool(name: str, payload: dict, _user: str = Depends(require_mcp_auth)) -> Any:
    dispatch = {
        "query_logs": lambda p: run_query_logs(p["service"], p["error_summary"], p.get("limit", 5)),
        "retrieve_runbooks": lambda p: run_retrieve_runbooks(
            p["query"], p.get("service", ""), p.get("top_k", 3)
        ),
        "create_ticket": lambda p: run_create_ticket(
            p["service"], p["severity"], p["recommendation"], p["runbook_id"]
        ),
        "get_metrics": lambda p: run_get_metrics(p["service"]),
    }
    if name not in dispatch:
        raise HTTPException(status_code=404, detail="unknown tool")
    try:
        result = dispatch[name](payload)
        # Normalize list results — FastAPI response model and clients expect JSON objects
        if isinstance(result, list):
            return {"logs": result, "count": len(result)}
        return result
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
