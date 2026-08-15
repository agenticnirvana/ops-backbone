"""HTTP client for the hosted Ops MCP server (Basic Auth)."""

from __future__ import annotations

import os
from typing import Any

import httpx

MCP_HTTP_URL = os.getenv("MCP_HTTP_URL", "http://mcp-server:8081").rstrip("/")
MCP_BASIC_USER = os.getenv("MCP_BASIC_USER", "mcp")
MCP_BASIC_PASSWORD = os.getenv("MCP_BASIC_PASSWORD", "mcp-secret")
MCP_HTTP_ENABLED = os.getenv("MCP_HTTP_ENABLED", "true").lower() == "true"


def mcp_http_call(tool: str, payload: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    """Invoke POST /tools/{name} on the hosted MCP server."""
    url = f"{MCP_HTTP_URL}/tools/{tool}"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            json=payload,
            auth=(MCP_BASIC_USER, MCP_BASIC_PASSWORD),
        )
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data


def mcp_server_health() -> dict[str, Any]:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(
            f"{MCP_HTTP_URL}/health",
            auth=(MCP_BASIC_USER, MCP_BASIC_PASSWORD),
        )
        response.raise_for_status()
        return response.json()
