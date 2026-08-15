"""Prometheus metrics exporter for demo service SLO gauges."""

from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("metrics-exporter")

METRICS_FILE = Path(os.getenv("METRICS_FILE", "/fixtures/metrics/services.json"))
PORT = int(os.getenv("PORT", "9100"))

GAUGES = {
    "cpu_percent": Gauge("service_cpu_percent", "CPU utilization percent", ["service"]),
    "error_rate_5m": Gauge("service_error_rate", "5m error rate", ["service"]),
    "p95_latency_ms": Gauge("service_p95_latency_ms", "P95 latency ms", ["service"]),
    "active_incidents": Gauge("service_active_incidents", "Active incidents", ["service"]),
}


def load_metrics() -> dict:
    if not METRICS_FILE.is_file():
        logger.warning("Metrics file missing: %s", METRICS_FILE)
        return {}
    return json.loads(METRICS_FILE.read_text(encoding="utf-8"))


def refresh_gauges() -> None:
    data = load_metrics()
    for service, values in data.items():
        for key, gauge in GAUGES.items():
            gauge.labels(service=service).set(float(values.get(key, 0.0)))


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/metrics", "/health"):
            self.send_response(404)
            self.end_headers()
            return

        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        refresh_gauges()
        payload = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        logger.debug(format, *args)


def main() -> None:
    refresh_gauges()
    server = HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    logger.info("Metrics exporter listening on :%s", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
