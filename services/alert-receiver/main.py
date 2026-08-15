"""Alertmanager webhook adapter — forwards fixtures to the LangGraph agent."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("alert-receiver")

AGENT_URL = os.getenv("AGENT_URL", "http://agent:8000").rstrip("/")
FIXTURES_DIR = Path(os.getenv("FIXTURES_DIR", "/fixtures/alerts"))


class AgentInvokeResponse(BaseModel):
    thread_id: str
    status: str
    classification: str | None = None
    recommendation: str | None = None
    runbook_id: str | None = None
    requires_hitl: bool = False
    ticket: dict[str, Any] | None = None


class WebhookResponse(BaseModel):
    alert_name: str
    agent_response: AgentInvokeResponse


class AlertmanagerPayload(BaseModel):
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    commonLabels: dict[str, str] = Field(default_factory=dict)


app = FastAPI(title="Alert Receiver", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Fixture not found: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _invoke_agent(alert: dict[str, Any]) -> AgentInvokeResponse:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{AGENT_URL}/invoke", json=alert)
        response.raise_for_status()
        data = response.json()
    return AgentInvokeResponse.model_validate(data)


@app.post("/webhook/alert/{fixture_name}", response_model=WebhookResponse)
def webhook_fixture(fixture_name: str) -> WebhookResponse:
    alert = _load_fixture(fixture_name)
    logger.info("Invoking agent for fixture=%s service=%s", fixture_name, alert.get("service"))
    agent_response = _invoke_agent(alert)
    return WebhookResponse(alert_name=fixture_name, agent_response=agent_response)


@app.post("/webhook/alertmanager", response_model=WebhookResponse)
def webhook_alertmanager(payload: AlertmanagerPayload) -> WebhookResponse:
    if not payload.alerts:
        raise HTTPException(status_code=422, detail="No alerts in payload")

    first = payload.alerts[0]
    labels = {**payload.commonLabels, **first.get("labels", {})}
    alert = {
        "service": labels.get("service", "unknown-service"),
        "severity": labels.get("severity", "P2"),
        "error_summary": first.get("annotations", {}).get("summary", "Alertmanager webhook"),
        "log_snippet": first.get("annotations", {}).get("description", ""),
    }
    agent_response = _invoke_agent(alert)
    return WebhookResponse(alert_name=labels.get("alertname", "alertmanager"), agent_response=agent_response)
