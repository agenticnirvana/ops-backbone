"""Fire-and-forget dashboard metrics to the platform gateway."""

from __future__ import annotations

import os
from typing import Any

import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8080").rstrip("/")


def _post(payload: dict[str, Any]) -> None:
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(f"{GATEWAY_URL}/api/internal/dashboard/runs", json=payload)
    except Exception:
        pass


def record_run_start(**kwargs: Any) -> None:
    _post({"event": "start", **kwargs})


def record_run_finish(**kwargs: Any) -> None:
    _post({"event": "finish", **kwargs})
