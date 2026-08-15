#!/usr/bin/env bash
# Regenerate walkthrough mockup PNGs from the live v3.4 Platform UI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${MOCKUP_BASE_URL:-http://localhost:8080}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! curl -sf "$BASE/api/health" >/dev/null 2>&1; then
  echo "Gateway not reachable at $BASE — start with: docker compose -p agentops-design-1 -f deploy/docker-compose.yml up -d gateway" >&2
  exit 1
fi

if [[ ! -d "$SCRIPT_DIR/node_modules/playwright" ]]; then
  echo "Installing Playwright (one-time)…"
  (cd "$SCRIPT_DIR" && npm init -y >/dev/null 2>&1 && npm install playwright --silent)
  (cd "$SCRIPT_DIR" && npx playwright install chromium)
fi

node "$SCRIPT_DIR/capture-mockups.mjs"
