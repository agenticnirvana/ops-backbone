"""Runbook Knowledge MCP server — RAG + catalog tools (port 8083)."""

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
from mcp_server.tools_internal import run_get_runbook_by_id, run_list_runbooks, run_retrieve_runbooks

SERVICE_ID = "mcp-rag-server"
PORT = int(os.getenv("MCP_PORT", "8083"))

app = FastAPI(title="Runbook RAG MCP Server", version="1.0.0")


@app.get("/health")
def health(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "status": "ok",
        "service": SERVICE_ID,
        "phase": 1,
        "auth": "basic",
        "tools": ["retrieve_runbooks", "list_runbooks", "get_runbook_by_id"],
    }


@app.get("/tools")
def list_tools(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "tools": [
            {"name": "retrieve_runbooks", "description": "Semantic search over Chroma runbook index"},
            {"name": "list_runbooks", "description": "Catalog all markdown runbooks on disk"},
            {"name": "get_runbook_by_id", "description": "Fetch runbook markdown snippet by ID"},
        ],
        "transport": "http+json",
        "auth": "basic",
    }


@app.post("/tools/{name}")
def call_tool(name: str, payload: dict, _user: str = Depends(require_mcp_auth)) -> Any:
    dispatch = {
        "retrieve_runbooks": lambda p: run_retrieve_runbooks(
            p["query"], p.get("service", ""), p.get("top_k", 3)
        ),
        "list_runbooks": lambda p: run_list_runbooks(),
        "get_runbook_by_id": lambda p: run_get_runbook_by_id(
            p["runbook_id"], p.get("max_chars", 1200)
        ),
    }
    if name not in dispatch:
        raise HTTPException(status_code=404, detail="unknown tool")
    try:
        result = dispatch[name](payload)
        if isinstance(result, list):
            return {"items": result, "count": len(result)}
        return result
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
