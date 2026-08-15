"""Pytest wrapper for CI/CD eval gate."""

import os

import pytest

os.environ["MOCK_LLM"] = "true"


@pytest.fixture(scope="module", autouse=True)
def build_index():
    from rag.build_index import build_index as bi

    bi()


def test_run_evals_passes_with_mock_llm():
    from evals.run_evals import run_evals

    report = run_evals()
    assert report["case_count"] >= 4, "golden dataset should include capstone cases"
    assert report["passed"] is True, report
    averages = report["averages"]
    thresholds = report["thresholds"]
    for metric, threshold in thresholds.items():
        if metric == "p95_latency_ms":
            assert averages[metric] <= threshold, f"{metric} exceeded threshold"
        else:
            assert averages[metric] >= threshold, f"{metric} below threshold"
