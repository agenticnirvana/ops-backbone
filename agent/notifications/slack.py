"""Slack incoming-webhook notifications for HITL approval requests."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
PLATFORM_PUBLIC_URL = os.getenv("PLATFORM_PUBLIC_URL", "http://localhost:8080").rstrip("/")
SLACK_NOTIFY_ENABLED = os.getenv("SLACK_NOTIFY_ENABLED", "true").lower() == "true"


def change_run_id(thread_id: str) -> str:
    return f"CR-{(thread_id or '0000')[:4].upper()}"


def build_hitl_slack_payload(
    *,
    thread_id: str,
    service: str,
    severity: str,
    recommendation: str | None,
    runbook_id: str | None,
    source: str,
) -> dict[str, Any]:
    cr = change_run_id(thread_id)
    rec = (recommendation or "Sensitive production change requires operator approval.").strip()
    if len(rec) > 500:
        rec = rec[:497] + "..."

    ops_url = f"{PLATFORM_PUBLIC_URL}/?view=opspilot&thread={thread_id}"
    text = f"HITL required — {service} ({severity}) · {cr}"

    return {
        "text": text,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Human approval required", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{service}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                    {"type": "mrkdwn", "text": f"*Change run:*\n{cr}"},
                    {"type": "mrkdwn", "text": f"*Runbook:*\n{runbook_id or '—'}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommendation:*\n{rec}"},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Source: `{source}` · thread `{thread_id[:8]}…` · OPA allow P1 destructive",
                    }
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open OpsPilot"},
                        "url": ops_url,
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Platform UI"},
                        "url": PLATFORM_PUBLIC_URL,
                    },
                ],
            },
        ],
    }


def notify_hitl_required(
    *,
    thread_id: str,
    service: str,
    severity: str,
    recommendation: str | None = None,
    runbook_id: str | None = None,
    source: str = "agent",
) -> bool:
    """Post HITL approval request to Slack. Returns True if sent."""
    if not SLACK_NOTIFY_ENABLED or not SLACK_WEBHOOK_URL:
        logger.debug("Slack HITL notification skipped (webhook not configured)")
        return False

    payload = build_hitl_slack_payload(
        thread_id=thread_id,
        service=service,
        severity=severity,
        recommendation=recommendation,
        runbook_id=runbook_id,
        source=source,
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()
        logger.info("Slack HITL notification sent for thread=%s service=%s", thread_id, service)
        return True
    except Exception as exc:
        logger.warning("Slack HITL notification failed: %s", exc)
        return False
