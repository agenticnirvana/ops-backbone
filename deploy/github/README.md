# GitHub governance

Private backbone: [agenticnirvana/ops-backbone](https://github.com/agenticnirvana/ops-backbone)

This is **not** the student-facing course repository. Students should receive a later clean squash with a course name. Author on this history is `AgentOps Platform`, not a personal identity.

## What ships

| Piece | Path |
|---|---|
| Pre-commit | `.pre-commit-config.yaml` |
| Local gate | `scripts/ci/local-gate.sh` |
| CI (lint / unit / secret-scan) | `.github/workflows/ci.yml` |
| Eval gate (required check) | `.github/workflows/eval-gate.yml` |
| Promote with environment reviewers | `.github/workflows/promote.yml` |
| CODEOWNERS | `.github/CODEOWNERS` |
| Environments / required checks | `deploy/github/config.yml` |

## One-time GitHub settings

1. Settings → Environments → create `staging` and `production` with required reviewers (four-eyes).
2. Settings → Branches → protect `main` with: `ci / lint`, `ci / unit`, `ci / secret-scan`, `eval-gate / golden-set`.
3. Settings → Secrets: `GOVERNANCE_WEBHOOK_URL`, `GOVERNANCE_WEBHOOK_TOKEN`, ingestion secrets.
4. Developers: `pip install pre-commit && pre-commit install`

Promote a SHA: Actions → **promote** → Run workflow → pick `staging` or `production`.
GitHub pauses the job until environment reviewers approve.
