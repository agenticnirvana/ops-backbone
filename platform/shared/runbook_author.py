"""Draft a new SRE runbook from an unmatched alert and optionally embed it."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from agent.llm import call_llm


def slug_runbook_id(service: str, summary: str) -> str:
    raw = f"{service} {summary}".lower()
    tokens = re.findall(r"[a-z0-9]+", raw)
    skip = {"the", "a", "an", "on", "in", "of", "and", "for", "to", "http", "https", "error"}
    kept = [t for t in tokens if t not in skip and not t.isdigit()][:6]
    if not kept:
        kept = ["unknown", "incident"]
    slug = "-".join(kept)
    return slug[:72].strip("-") or "unknown-incident"


def draft_runbook_markdown(
    *,
    service: str,
    severity: str,
    error_summary: str,
    log_snippet: str = "",
    recommendation: str = "",
) -> dict[str, Any]:
    runbook_id = slug_runbook_id(service, error_summary)
    system = (
        "Write a new SRE runbook in GitHub-flavored markdown. "
        "Return JSON: {title, markdown}. The markdown MUST start with '# {title}' then "
        "**Service:**, **Severity:**, **Triggers:**, ## Diagnosis, ## Remediation, ## Verification, ## Escalation. "
        "Do not claim an existing catalog runbook applies. Keep it operational and specific to the alert."
    )
    user = json.dumps(
        {
            "service": service,
            "severity": severity,
            "error_summary": error_summary,
            "log_snippet": log_snippet,
            "investigation_notes": recommendation,
        }
    )
    raw = call_llm(system, user)
    title = f"{service} — {error_summary[:80]}"
    markdown = ""
    try:
        data = json.loads(raw.strip().strip("`").replace("json", "", 1))
        title = data.get("title") or title
        markdown = data.get("markdown") or ""
    except json.JSONDecodeError:
        markdown = raw
    if not markdown.strip().startswith("#"):
        markdown = _template_markdown(
            title=title,
            service=service,
            severity=severity,
            error_summary=error_summary,
            log_snippet=log_snippet,
            recommendation=recommendation,
        )
    return {"runbook_id": runbook_id, "title": title, "markdown": markdown}


def _template_markdown(
    *,
    title: str,
    service: str,
    severity: str,
    error_summary: str,
    log_snippet: str,
    recommendation: str,
) -> str:
    return (
        f"# {title}\n\n"
        f"**Service:** {service}  \n"
        f"**Severity:** {severity}  \n"
        f"**Triggers:** {error_summary}\n\n"
        f"## Diagnosis\n\n"
        f"1. Confirm the error signature in logs: `{log_snippet[:180] or error_summary}`\n"
        f"2. Check error rate, latency, and last deploy for `{service}`\n"
        f"3. Rule out known catalog runbooks — this signature did not meet the RAG confidence gate\n\n"
        f"## Remediation\n\n"
        f"{recommendation or 'Investigate with logs and metrics before changing production. Requires HITL approval.'}\n\n"
        f"## Verification\n\n"
        f"- Error rate for `{service}` returns below the alert threshold\n"
        f"- Synthetic probe for the failing path succeeds\n\n"
        f"## Escalation\n\n"
        f"Page the service owner if the signature recurs within 1 hour after mitigation.\n"
    )


def persist_runbook(*, runbook_id: str, markdown: str, triggered_by: str = "platform") -> dict[str, Any]:
    url = os.getenv("INGESTION_URL", "http://runbook-ingestion:8092").rstrip("/")
    token = os.getenv("INGESTION_API_TOKEN", "design1-ingestion-token-change-me")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{url}/v1/ingest/runbooks",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"runbook_id": runbook_id, "markdown": markdown, "triggered_by": triggered_by, "reindex": True},
        )
        r.raise_for_status()
        return r.json()
