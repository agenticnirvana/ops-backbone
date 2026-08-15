"""Runbook ingestion service configuration."""

from __future__ import annotations

import os
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://agentops:agentops@postgres:5432/agentops",
)
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "/data/chroma"))
RUNBOOKS_DIR = Path(os.getenv("RUNBOOKS_DIR", "/data/runbooks"))
SEED_RUNBOOKS_DIR = Path(os.getenv("SEED_RUNBOOKS_DIR", "/seed/runbooks"))
INDEX_MANIFEST_PATH = Path(os.getenv("INDEX_MANIFEST_PATH", str(CHROMA_PATH / "active.json")))

INGESTION_API_TOKEN = os.getenv("INGESTION_API_TOKEN", "design1-ingestion-token-change-me")
RUNBOOK_CRON_ENABLED = env_bool("RUNBOOK_CRON_ENABLED", True)
RUNBOOK_CRON_SCHEDULE = os.getenv("RUNBOOK_CRON_SCHEDULE", "0 0 * * *")

GOOGLE_DRIVE_ENABLED = env_bool("GOOGLE_DRIVE_ENABLED", False)
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "/secrets/google-service-account.json",
)

# Propagate paths to the shared rag indexer module.
os.environ.setdefault("CHROMA_PATH", str(CHROMA_PATH))
os.environ.setdefault("RUNBOOKS_DIR", str(RUNBOOKS_DIR))
os.environ.setdefault("INDEX_MANIFEST_PATH", str(INDEX_MANIFEST_PATH))
