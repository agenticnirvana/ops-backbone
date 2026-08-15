"""Slack HITL notification payload tests."""

from notifications.slack import build_hitl_slack_payload, change_run_id


def test_change_run_id():
    assert change_run_id("abcd-1234-5678") == "CR-ABCD"


def test_build_hitl_slack_payload_includes_ops_link():
    payload = build_hitl_slack_payload(
        thread_id="abcd-1234",
        service="checkout-service",
        severity="P1",
        recommendation="Increase REDIS_MAX_CONNECTIONS",
        runbook_id="checkout-redis-pool",
        source="alert-receiver",
    )
    assert payload["text"].startswith("HITL required")
    blocks = payload["blocks"]
    actions = next(b for b in blocks if b["type"] == "actions")
    urls = [el["url"] for el in actions["elements"]]
    assert any("thread=abcd-1234" in u for u in urls)
