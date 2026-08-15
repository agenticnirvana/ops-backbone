"""LLM-as-judge scorer for golden-set evaluations."""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm


def judge_recommendation(
    *,
    alert: dict[str, Any],
    recommendation: str,
    expected_runbook_id: str | None,
    actual_runbook_id: str | None,
    grounded_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Return {score: 0-1, reason, raw} from an LLM-as-judge prompt."""
    system = (
        "You are an SRE LLM-as-judge evaluator. Score whether the agent recommendation "
        "is grounded, specific, and aligned with the expected runbook. "
        "Return JSON only: {\"score\": number between 0 and 1, \"reason\": string}."
    )
    user = json.dumps(
        {
            "alert": alert,
            "recommendation": (recommendation or "")[:800],
            "expected_runbook_id": expected_runbook_id,
            "actual_runbook_id": actual_runbook_id,
            "grounded_keywords": grounded_keywords or [],
        }
    )
    raw = call_llm(system, user)
    score = 0.5
    reason = (raw or "").strip()[:400]
    try:
        data = json.loads(raw.strip().strip("`").replace("json", "", 1))
        score = max(0.0, min(1.0, float(data.get("score", 0.5))))
        reason = str(data.get("reason") or reason)[:400]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {"score": round(score, 4), "reason": reason, "raw": raw[:800]}
