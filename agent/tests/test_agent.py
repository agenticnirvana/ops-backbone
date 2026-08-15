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


def test_graph_invoke():
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
