"""HITL pause → approve → ticket flow tests."""

import os

import pytest

os.environ["MOCK_LLM"] = "true"


@pytest.fixture(scope="module", autouse=True)
def build_index():
    from rag.build_index import build_index as bi

    bi()


def test_hitl_pause_and_approve_creates_ticket():
    from agent.graph import get_graph
    from observability.setup import build_invoke_config

    graph = get_graph()
    thread_id = "hitl-test-thread"
    config = build_invoke_config("hitl-test", session_id=thread_id)
    alert = {
        "service": "checkout-service",
        "severity": "P1",
        "error_summary": "HTTP 500 spike on /checkout",
        "log_snippet": "Timeout waiting for connection pool (Redis)",
    }

    result = graph.invoke({"alert": alert}, config=config)
    assert result.get("requires_hitl") is True
    assert graph.get_state(config).next  # paused at hitl_gate

    graph.update_state(config, {"hitl_approved": True})
    final = graph.invoke(None, config=config)
    assert final.get("ticket", {}).get("ticket_id")
    assert not graph.get_state(config).next


def test_hitl_denied_no_ticket():
    from agent.graph import build_graph
    from observability.setup import build_invoke_config

    graph = build_graph(enable_hitl=True)
    thread_id = "hitl-deny-thread"
    config = build_invoke_config("hitl-deny", session_id=thread_id)
    alert = {
        "service": "payment-api",
        "severity": "P1",
        "error_summary": "High CPU",
        "log_snippet": "retry storm",
    }

    graph.invoke({"alert": alert}, config=config)
    assert graph.get_state(config).next
    # Simulate deny — do not approve; state stays interrupted
    state = graph.get_state(config)
    assert state.values.get("hitl_approved") is not True


def test_api_approve_endpoint():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    alert = {
        "service": "checkout-service",
        "severity": "P1",
        "error_summary": "HTTP 500 spike on /checkout",
        "log_snippet": "Redis pool timeout",
        "thread_id": "api-hitl-thread",
    }
    r1 = client.post("/invoke", json=alert)
    assert r1.status_code == 200
    body = r1.json()
    assert body["status"] == "awaiting_hitl"
    assert body["thread_id"] == "api-hitl-thread"

    r2 = client.post("/approve", json={"thread_id": "api-hitl-thread", "approved": True})
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"
    assert r2.json()["ticket"]["ticket_id"]
