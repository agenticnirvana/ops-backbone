"""Pytest defaults — CI fast path only; production stacks do not use these."""

import os

import pytest

os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("EMBEDDING_BACKEND", "hash")
os.environ.setdefault("LOG_QUERY_BACKEND", "fixture")
os.environ.setdefault("METRICS_QUERY_BACKEND", "fixture")


@pytest.fixture(scope="session", autouse=True)
def ensure_runbook_index():
    from rag.build_index import build_index

    build_index(mode="full")
