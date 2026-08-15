#!/usr/bin/env bash
# Developer pre-push gate — lint, secrets hygiene, unit tests. Eval gate is CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== pre-commit / local CI gate =="
echo "course root: $ROOT"

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit run --all-files --show-diff-on-failure
else
  echo "pre-commit not installed — running ruff + key hooks directly"
  python -m pip show ruff >/dev/null 2>&1 || python -m pip install -q ruff
  (cd agent && ruff check agent api rag observability evals tests)
  python - <<'PY'
from pathlib import Path
needles = ("BEGIN OPENSSH PRIVATE KEY", "AWS_SECRET_ACCESS_KEY", "sk-lf-")
bad = []
skip = {".git", "node_modules", ".venv", "agent/.venv", "scripts/node_modules"}
for path in Path(".").rglob("*"):
    if any(part in skip for part in path.parts):
        continue
    if not path.is_file() or path.suffix in {".png", ".jpg", ".webp", ".ico"}:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for n in needles:
        if n in text and "example" not in path.name.lower() and "placeholder" not in text.lower()[:400]:
            # allow documented example keys in .env.example / docs
            if path.name in {".env.example", "README.md"} or "design1-local" in text:
                continue
            if path.name == ".env":
                bad.append(str(path))
                break
if bad:
    raise SystemExit("possible secrets in: " + ", ".join(bad))
print("secret hygiene ok")
PY
fi

echo "== unit tests (MOCK_LLM) =="
(
  cd agent
  export MOCK_LLM=true
  python -m rag.build_index
  pytest -q tests
)

echo "local gate passed. Eval gate runs in GitHub Actions (eval-gate.yml)."
