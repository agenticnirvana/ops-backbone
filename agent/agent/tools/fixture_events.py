"""Query bundled domain event logs (HRIS, wiki audit, etc.) — teaching fixtures, not mocks."""

from __future__ import annotations

import json
from pathlib import Path

SAMPLE_ROOT = Path(__file__).resolve().parents[2] / "sample_data"


def query_fixture_events(domain: str, service: str, query: str = "", limit: int = 5) -> list[dict]:
    """Return recent events from sample_data/<domain>/events/<service>.jsonl."""
    path = SAMPLE_ROOT / domain / "events" / f"{service}.jsonl"
    if not path.exists():
        return [{"message": f"No fixture events for {domain}/{service}", "level": "info"}]

    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if query:
        q = query.lower()
        events = [e for e in events if q in json.dumps(e).lower()]

    return events[-limit:]
