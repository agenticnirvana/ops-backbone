"""Governance placeholders, four-eyes promotions, GitHub ingest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PLATFORM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM))

os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("USE_MCP_TOOLS", "false")
os.environ.setdefault("MCP_HTTP_ENABLED", "false")
os.environ.setdefault("AGENTREGISTRY_ENABLED", "false")


def test_github_placeholders():
    from shared.governance import control_catalog, github_config

    cfg = github_config()
    assert cfg["org"] == "YOUR_GITHUB_ORG"
    assert cfg["repo"] == "YOUR_GITHUB_REPO"
    assert cfg["wired"] is False
    assert "eval-gate / golden-set" in cfg["required_checks"]
    assert len(control_catalog()) >= 8


def test_governance_api_and_four_eyes():
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)
    op = client.post("/api/auth/login", json={"email": "operator@agentops.local", "password": "operator123"})
    assert op.status_code == 200
    op_headers = {"Authorization": f"Bearer {op.json()['access_token']}"}

    overview = client.get("/api/governance/overview", headers=op_headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["github"]["org"] == "YOUR_GITHUB_ORG"
    assert any(c["id"] == "GOV-04" for c in body["controls"])

    created = client.post(
        "/api/governance/promotions",
        headers=op_headers,
        json={"environment": "production", "reason": "pytest four-eyes", "sha": "deadbeef"},
    )
    assert created.status_code == 200
    promo_id = created.json()["id"]

    self_approve = client.post(
        f"/api/governance/promotions/{promo_id}/decide",
        headers=op_headers,
        json={"approved": True, "note": "should fail"},
    )
    assert self_approve.status_code == 409

    admin = client.post("/api/auth/login", json={"email": "admin@agentops.local", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    decided = client.post(
        f"/api/governance/promotions/{promo_id}/decide",
        headers=admin_headers,
        json={"approved": True, "note": "admin four-eyes"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["decided_by"] == "admin@agentops.local"


def test_github_webhook_ingest():
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email": "operator@agentops.local", "password": "operator123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    ingested = client.post(
        "/api/governance/github/webhook",
        json={
            "workflow_run": {
                "name": "eval-gate / golden-set",
                "conclusion": "success",
                "head_sha": "abc123abc123abc123abc123abc123abc123abc1",
                "head_branch": "main",
                "html_url": "",
                "display_title": "pytest webhook",
            },
            "sender": {"login": "github-actions"},
        },
    )
    assert ingested.status_code == 200
    assert ingested.json()["conclusion"] == "success"
    pipelines = client.get("/api/governance/pipelines", headers=headers)
    assert pipelines.status_code == 200
    assert any(r["check_name"] == "eval-gate / golden-set" for r in pipelines.json()["runs"])
