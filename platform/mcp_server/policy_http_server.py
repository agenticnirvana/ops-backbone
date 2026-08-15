"""Policy & Guardrails MCP server — OPA preview tools (port 8082)."""

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
from mcp_server.tools_internal import run_check_opa_policy, run_list_policy_rules, run_preview_hitl_gate

SERVICE_ID = "mcp-policy-server"
PORT = int(os.getenv("MCP_PORT", "8082"))

app = FastAPI(title="Policy MCP Server", version="1.0.0")


@app.get("/health")
def health(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "status": "ok",
        "service": SERVICE_ID,
        "phase": 4,
        "auth": "basic",
        "tools": ["check_opa_policy", "list_policy_rules", "preview_hitl_gate"],
    }


@app.get("/tools")
def list_tools(_user: str = Depends(require_mcp_auth)) -> dict:
    return {
        "tools": [
            {"name": "check_opa_policy", "description": "Evaluate recommendation against OPA/Rego policy"},
            {"name": "list_policy_rules", "description": "List human-readable guardrail rules in Design 1"},
            {"name": "preview_hitl_gate", "description": "Preview OPA verdict + whether HITL would pause the graph"},
        ],
        "transport": "http+json",
        "auth": "basic",
    }


@app.post("/tools/{name}")
def call_tool(name: str, payload: dict, _user: str = Depends(require_mcp_auth)) -> Any:
    dispatch = {
        "check_opa_policy": lambda p: run_check_opa_policy(
            p["service"], p["severity"], p["recommendation"]
        ),
        "list_policy_rules": lambda p: run_list_policy_rules(),
        "preview_hitl_gate": lambda p: run_preview_hitl_gate(
            p["service"], p["severity"], p["recommendation"]
        ),
    }
    if name not in dispatch:
        raise HTTPException(status_code=404, detail="unknown tool")
    try:
        return dispatch[name](payload)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
