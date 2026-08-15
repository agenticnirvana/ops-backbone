#!/usr/bin/env python3
"""Seed shared tools so each design has data in its own slice.

Langfuse: one project per design (keys from env).
Tempo / Phoenix: OTLP traces tagged agentops.design=d1|d2|d3.
Mimir is filled by Prometheus remote_write (restart prometheus after config change).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

LANGFUSE = os.environ.get("LANGFUSE_PUBLIC_URL", "http://localhost:3000").rstrip("/")
OTLP = os.environ.get("OTLP_HTTP", "http://localhost:4318").rstrip("/")
TEMPO_OTLP = os.environ.get("TEMPO_OTLP_HTTP", "http://localhost:4319").rstrip("/")
MIMIR = os.environ.get("MIMIR_URL", "http://localhost:9009").rstrip("/")

KEYS = {
    "d1": (
        os.environ.get("LANGFUSE_D1_PUBLIC_KEY") or os.environ.get("LANGFUSE_PUBLIC_KEY") or "",
        os.environ.get("LANGFUSE_D1_SECRET_KEY") or os.environ.get("LANGFUSE_SECRET_KEY") or "",
    ),
    "d2": (
        os.environ.get("LANGFUSE_D2_PUBLIC_KEY") or "",
        os.environ.get("LANGFUSE_D2_SECRET_KEY") or "",
    ),
    "d3": (
        os.environ.get("LANGFUSE_D3_PUBLIC_KEY") or "",
        os.environ.get("LANGFUSE_D3_SECRET_KEY") or "",
    ),
}

ALERTS = [
    ("CheckoutHighErrorRate", "checkout-service", "P1", "checkout-redis-pool"),
    ("PaymentHighCPU", "payment-api", "P1", "payment-high-cpu"),
    ("AuthErrorSpike", "auth-service", "P2", "auth-error-spike"),
    ("DatabasePoolExhausted", "order-service", "P1", "db-pool-exhausted"),
]


def req(url, method="GET", body=None, headers=None, timeout=15):
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        return 0, str(exc.reason).encode()


def seed_langfuse(design: str, pk: str, sk: str) -> int:
    if not pk or not sk:
        print(f"skip Langfuse {design}: missing keys")
        return 0
    import base64

    token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    n = 0
    for alert, service, sev, runbook in ALERTS:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        trace_id = uuid.uuid4().hex
        batch = [
            {
                "id": str(uuid.uuid4()),
                "type": "trace-create",
                "timestamp": now,
                "body": {
                    "id": trace_id,
                    "name": f"ops-triage-{design}-{alert}",
                    "userId": "operator@agentops.local",
                    "sessionId": f"{design}-{service}",
                    "metadata": {"design": design, "alert_name": alert, "runbook_id": runbook, "source": "seed"},
                    "tags": [design, "seed", service, sev],
                    "input": {"service": service, "severity": sev, "alert_name": alert},
                    "output": {"runbook_id": runbook, "status": "walkthrough"},
                },
            }
        ]
        status, raw = req(
            f"{LANGFUSE}/api/public/ingestion",
            method="POST",
            body={"batch": batch},
            headers={"Authorization": f"Basic {token}"},
        )
        if status in (200, 201, 207):
            n += 1
        else:
            print(f"Langfuse {design} {alert} failed {status}: {raw[:300]!r}")
    print(f"Langfuse {design}: {n} traces")
    return n


def otlp_payload(design: str, service: str, name: str) -> dict:
    now_ns = str(time.time_ns())
    end_ns = str(time.time_ns() + 12_000_000)
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "ops-triage-agent"}},
                        {"key": "agentops.design", "value": {"stringValue": design}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "ops-triage"},
                        "spans": [
                            {
                                "traceId": uuid.uuid4().hex,
                                "spanId": uuid.uuid4().hex[:16],
                                "name": name,
                                "kind": 1,
                                "startTimeUnixNano": now_ns,
                                "endTimeUnixNano": end_ns,
                                "attributes": [
                                    {"key": "service", "value": {"stringValue": service}},
                                    {"key": "agentops.design", "value": {"stringValue": design}},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def seed_otlp(url: str, label: str) -> int:
    n = 0
    for design in ("d1", "d2", "d3"):
        for alert, service, _sev, _rb in ALERTS:
            status, raw = req(
                f"{url}/v1/traces",
                method="POST",
                body=otlp_payload(design, service, f"{design} · {alert}"),
            )
            if status in (200, 201, 202):
                n += 1
            else:
                print(f"{label} {design} {alert} failed {status}: {raw[:200]!r}")
    print(f"{label}: {n} spans")
    return n


def check_mimir() -> None:
    status, raw = req(f"{MIMIR}/prometheus/api/v1/query?query=service_error_rate")
    print(f"Mimir query status={status} body={raw[:400]!r}")


def main() -> None:
    total = 0
    for did, (pk, sk) in KEYS.items():
        total += seed_langfuse(did, pk, sk)
    seed_otlp(OTLP, "otel-collector")
    seed_otlp(TEMPO_OTLP, "tempo-direct")
    check_mimir()
    print(f"done. langfuse traces={total}")


if __name__ == "__main__":
    main()
