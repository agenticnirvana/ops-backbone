"""Platform integration tests."""

import os
import sys
from pathlib import Path

import pytest

PLATFORM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM))

os.environ["MOCK_LLM"] = "true"
os.environ["USE_MCP_TOOLS"] = "false"
os.environ["MCP_HTTP_ENABLED"] = "false"
os.environ["AGENTREGISTRY_ENABLED"] = "false"


@pytest.fixture(scope="module", autouse=True)
def build_index():
    agent_root = PLATFORM.parent / "agent"
    sys.path.insert(0, str(agent_root))
    from rag.build_index import build_index as bi

    bi()


def test_multi_agent_invoke():
    from multi_agent.graph import get_multi_agent_graph
    from observability.setup import build_invoke_config

    g = get_multi_agent_graph()
    alert = {"service": "payment-api", "severity": "P1", "error_summary": "High CPU", "log_snippet": "retry"}
    out = g.invoke({"alert": alert}, config=build_invoke_config("test", "multi-1"))
    assert out.get("worker_trace")
    assert "supervisor" in out["worker_trace"][0]
    assert len(out.get("delegation_events") or []) >= 3


def test_agent_registry_seed():
    from shared.agent_registry import list_registry_agents, seed_agent_registry

    seed_agent_registry()
    agents = list_registry_agents()
    assert len(agents) >= 10
    slugs = {a["slug"] for a in agents}
    assert "sre-supervisor" in slugs
    assert "mcp-ops-server" in slugs


def test_skills_registry():
    from shared.skill_registry import get_skill, list_skills, run_skill_script, seed_skills_registry

    seed_skills_registry()
    skills = list_skills()
    assert len(skills) >= 4
    assert any(s["slug"] == "severity-classifier" for s in skills)
    detail = get_skill("severity-classifier")
    assert detail and "skill_md" in detail
    out = run_skill_script("severity-classifier", "classify_severity.py", ["checkout redis pool timeout"])
    assert out["exit_code"] == 0
    assert out["result"].get("severity") == "P1"


def test_gateway_multi_and_registry_api():
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "admin@agentops.local", "password": "admin123"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    reg = client.get("/api/agents/registry", headers=headers)
    assert reg.status_code == 200
    assert reg.json()["total"] >= 10

    modes = client.get("/api/agents/modes", headers=headers)
    assert modes.status_code == 200
    assert {m["id"] for m in modes.json()["modes"]} >= {"standalone", "multi", "mcp"}

    mcp_cfg = client.get("/api/agents/mcp/config", headers=headers)
    assert mcp_cfg.status_code == 200
    assert mcp_cfg.json()["auth"] == "basic"

    from gateway.mcp_playground import list_playground_servers

    servers = list_playground_servers()
    assert len(servers) >= 3
    assert {s["id"] for s in servers} >= {"ops-local", "policy-local", "rag-local"}

    invoke = client.post(
        "/api/agents/invoke",
        headers=headers,
        json={
            "domain": "sre",
            "mode": "multi",
            "service": "payment-api",
            "severity": "P1",
            "error_summary": "CPU high",
            "log_snippet": "retry",
        },
    )
    assert invoke.status_code == 200
    body = invoke.json()
    assert body["mode"] == "multi"
    assert body.get("delegation_events")
    assert body.get("worker_trace")


def test_mcp_agent_invoke():
    from mcp_server.agent_graph import get_mcp_agent_graph
    from observability.setup import build_invoke_config

    g = get_mcp_agent_graph()
    alert = {"service": "auth-service", "severity": "P2", "error_summary": "5xx spike", "log_snippet": "jwt"}
    out = g.invoke({"alert": alert}, config=build_invoke_config("test", "mcp-1"))
    assert out.get("recommendation") or out.get("classification")


def test_gateway_auth_and_invoke():
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "operator@agentops.local", "password": "operator123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.post(
        "/api/agents/invoke",
        headers=headers,
        json={
            "domain": "sre",
            "mode": "standalone",
            "service": "payment-api",
            "severity": "P1",
            "error_summary": "CPU high",
            "log_snippet": "retry",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["mode"] == "standalone"


def test_gateway_hitl_approve_flow():
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "operator@agentops.local", "password": "operator123"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r2 = client.post(
        "/api/agents/invoke",
        headers=headers,
        json={
            "domain": "sre",
            "mode": "standalone",
            "thread_id": "gateway-hitl-1",
            "service": "checkout-service",
            "severity": "P1",
            "error_summary": "HTTP 500 spike on /checkout",
            "log_snippet": "Redis pool timeout",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "awaiting_hitl"

    r3 = client.post(
        "/api/agents/approve",
        headers=headers,
        json={"domain": "sre", "mode": "standalone", "thread_id": "gateway-hitl-1", "approved": True},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "completed"
    assert r3.json()["ticket"]["ticket_id"]
