"""In-process MCP tool implementations — used by the hosted MCP HTTP server."""

from __future__ import annotations

import shared.config  # noqa: F401 — agent on sys.path

from agent.tools.log_query import query_logs as _query_logs
from agent.tools.metrics_query import query_metrics as _query_metrics
from agent.tools.runbook_rag import format_runbook_context, retrieve_runbooks
from agent.tools.ticket_create import create_ticket as _create_ticket


def run_query_logs(service: str, error_summary: str, limit: int = 5) -> list[dict]:
    return _query_logs(service, error_summary, limit)


def run_retrieve_runbooks(query: str, service: str = "", top_k: int = 3) -> dict:
    chunks = retrieve_runbooks(query, service=service or None, top_k=top_k)
    return {"chunks": chunks, "context": format_runbook_context(chunks)}


def run_create_ticket(service: str, severity: str, recommendation: str, runbook_id: str) -> dict:
    return _create_ticket(service, severity, recommendation, runbook_id)


def run_get_metrics(service: str) -> dict:
    return _query_metrics(service)


def run_check_opa_policy(service: str, severity: str, recommendation: str) -> dict:
    from mcp_server.policy_eval import build_evaluation_result

    return build_evaluation_result(service=service, severity=severity, recommendation=recommendation)


def run_list_policy_rules() -> dict:
    from mcp_server.policy_eval import POLICY_RULES

    return {"rules": POLICY_RULES, "count": len(POLICY_RULES)}


def run_preview_hitl_gate(service: str, severity: str, recommendation: str) -> dict:
    from mcp_server.policy_eval import build_evaluation_result, is_destructive

    evaluation = build_evaluation_result(service=service, severity=severity, recommendation=recommendation)
    destructive = is_destructive(recommendation)
    hitl_required = destructive or severity in {"P1", "P2"}
    return {
        **evaluation,
        "hitl_required": hitl_required,
        "would_pause_graph": hitl_required,
    }


def run_list_runbooks() -> dict:
    import os
    from pathlib import Path

    root = Path(os.getenv("RUNBOOKS_DIR", "/data/runbooks"))
    if not root.is_dir():
        root = Path(__file__).resolve().parents[2] / "agent" / "rag" / "runbooks"
    runbooks = [
        {
            "id": path.stem,
            "title": path.stem.replace("-", " ").title(),
            "filename": path.name,
        }
        for path in sorted(root.glob("*.md"))
    ]
    return {"runbooks": runbooks, "count": len(runbooks)}


def run_get_runbook_by_id(runbook_id: str, max_chars: int = 1200) -> dict:
    import os
    from pathlib import Path

    root = Path(os.getenv("RUNBOOKS_DIR", "/data/runbooks"))
    if not root.is_dir():
        root = Path(__file__).resolve().parents[2] / "agent" / "rag" / "runbooks"
    path = root / f"{runbook_id}.md"
    if not path.is_file():
        return {"runbook_id": runbook_id, "found": False, "content": ""}
    text = path.read_text(encoding="utf-8")
    return {
        "runbook_id": runbook_id,
        "found": True,
        "title": runbook_id.replace("-", " ").title(),
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    }
