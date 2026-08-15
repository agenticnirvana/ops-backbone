"""Ops MCP Server — exposes AIOps tools via Model Context Protocol (stdio + HTTP)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure imports resolve
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM_ROOT))

from mcp_server.tools_impl import (
    mcp_create_ticket,
    mcp_get_metrics,
    mcp_query_logs,
    mcp_retrieve_runbooks,
)

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("ops-aiops-mcp", host="0.0.0.0", port=8081)


    @mcp.tool()
    def query_logs(service: str, error_summary: str, limit: int = 5) -> str:
        """Query recent error logs for a service."""
        return json.dumps(mcp_query_logs(service, error_summary, limit))


    @mcp.tool()
    def retrieve_runbooks(query: str, service: str = "", top_k: int = 3) -> str:
        """RAG retrieval against ops runbooks."""
        return json.dumps(mcp_retrieve_runbooks(query, service, top_k))


    @mcp.tool()
    def create_ticket(service: str, severity: str, recommendation: str, runbook_id: str) -> str:
        """Create an ops incident ticket."""
        return json.dumps(mcp_create_ticket(service, severity, recommendation, runbook_id))


    @mcp.tool()
    def get_metrics(service: str) -> str:
        """Get current service metrics (CPU, errors, latency)."""
        return json.dumps(mcp_get_metrics(service))


    if __name__ == "__main__":
        transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
        if transport == "http":
            mcp.run(transport="streamable-http")
        else:
            mcp.run(transport="stdio")

except ImportError:
    # Fallback HTTP-only server without mcp package
    if __name__ == "__main__":
        from fastapi import FastAPI
        import uvicorn

        app = FastAPI(title="Ops MCP Fallback")

        @app.get("/tools")
        def list_tools():
            return {
                "tools": [
                    {"name": "query_logs", "description": "Query error logs"},
                    {"name": "retrieve_runbooks", "description": "RAG runbook lookup"},
                    {"name": "create_ticket", "description": "Create incident ticket"},
                    {"name": "get_metrics", "description": "Service metrics"},
                ]
            }

        @app.post("/tools/{name}")
        def call_tool(name: str, payload: dict):
            dispatch = {
                "query_logs": lambda p: mcp_query_logs(p["service"], p["error_summary"], p.get("limit", 5)),
                "retrieve_runbooks": lambda p: mcp_retrieve_runbooks(p["query"], p.get("service", ""), p.get("top_k", 3)),
                "create_ticket": lambda p: mcp_create_ticket(
                    p["service"], p["severity"], p["recommendation"], p["runbook_id"]
                ),
                "get_metrics": lambda p: mcp_get_metrics(p["service"]),
            }
            if name not in dispatch:
                return {"error": "unknown tool"}
            return dispatch[name](payload)

        uvicorn.run(app, host="0.0.0.0", port=8081)
