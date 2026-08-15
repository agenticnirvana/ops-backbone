"""Smoke tests for ops triage agent."""

import os

import pytest

os.environ["MOCK_LLM"] = "true"


@pytest.fixture(scope="module", autouse=True)
def build_index():
    from rag.build_index import build_index as bi

    bi()


def test_rag_retrieval():
    from agent.tools.runbook_rag import retrieve_runbooks

    chunks = retrieve_runbooks("payment high CPU", service="payment-api", top_k=3)
    assert len(chunks) > 0
    assert chunks[0]["runbook_id"] == "payment-high-cpu"


def test_assess_rejects_thin_checkout_500():
    from agent.tools.runbook_rag import assess_runbook_match

    chunks = [
        {
            "runbook_id": "checkout-redis-pool",
            "similarity": 0.99,
            "content": "# Redis connection pool exhaustion **Service:** checkout-service **Severity:** P1",
        }
    ]
    match = assess_runbook_match(
        chunks, query="checkout-service 500 test", service="checkout-service"
    )
    assert match["matched"] is False
    assert match["runbook_id"] == "none"
    assert match["nearest"]["runbook_id"] == "checkout-redis-pool"


def test_assess_accepts_grounded_redis_signature():
    from agent.tools.runbook_rag import assess_runbook_match

    chunks = [
        {
            "runbook_id": "checkout-redis-pool",
            "similarity": 0.81,
            "content": "Redis connection pool exhaustion REDIS_MAX_CONNECTIONS Timeout waiting for connection pool",
        }
    ]
    match = assess_runbook_match(
        chunks,
        query="checkout-service HTTP 500 Timeout waiting for connection pool Redis",
        service="checkout-service",
    )
    assert match["matched"] is True
    assert match["runbook_id"] == "checkout-redis-pool"


def test_retrieve_gate_generic_500_is_unmatched():
    from agent.tools.runbook_rag import retrieve_with_gate

    gated = retrieve_with_gate("checkout-service 500 test", service="checkout-service", top_k=3)
    assert gated["gap"] is True
    assert gated["runbook_id"] == "none"
    from agent.graph import get_graph
    from observability.setup import build_invoke_config

    graph = get_graph()
    alert = {
        "service": "payment-api",
        "severity": "P1",
        "error_summary": "High CPU",
        "log_snippet": "retry storm",
    }
    config = build_invoke_config("test", session_id="test-thread")
    result = graph.invoke({"alert": alert}, config=config)
    assert result.get("classification")
    assert result.get("runbook_chunks")
    assert result.get("recommendation")


def test_api_health():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
