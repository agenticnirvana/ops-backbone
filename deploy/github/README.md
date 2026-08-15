# GitHub governance

Private backbone (now public): [agenticnirvana/ops-backbone](https://github.com/agenticnirvana/ops-backbone)

This is **not** the student-facing course repository. Students should receive a later clean squash with a course name. Author on this history is `AgentOps Platform`, not a personal identity.

Teaching decks (static, free): https://agenticnirvana.github.io/ops-backbone/

The live console + Langfuse / Weaviate / Elasticsearch / Ollama **cannot** run on GitHub Pages. That stack stays `docker compose` on a machine with RAM.

## What ships

| Piece | Path |
|---|---|
| Pre-commit | `.pre-commit-config.yaml` |
| Local gate | `scripts/ci/local-gate.sh` |
| CI (lint / unit / secret-scan) | `.github/workflows/ci.yml` |
| Eval gate (required check) | `.github/workflows/eval-gate.yml` |
| Teaching decks (GitHub Pages) | `.github/workflows/pages.yml` → https://agenticnirvana.github.io/ops-backbone/ |
| Promote with environment reviewers | `.github/workflows/promote.yml` |
| CODEOWNERS | `.github/CODEOWNERS` |
| Environments / required checks | `deploy/github/config.yml` |

## One-time GitHub settings

Protected branches and CODEOWNERS-as-required-reviewers need **GitHub Pro** (or a public repo) on a personal private repository. `ops-backbone` is private on a Free user account, so the API returns 403 until you upgrade or change visibility.

After Pro (or making the repo public), run:

```bash
gh api --method PUT repos/agenticnirvana/ops-backbone/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "ci / lint"},
      {"context": "ci / unit"},
      {"context": "ci / secret-scan"},
      {"context": "eval-gate / golden-set"}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

Until then, eval-gate still **runs** on every push and pull request; it just cannot block the merge button.

1. Settings → Environments → create `staging` and `production` with required reviewers (four-eyes).
2. Settings → Branches → protect `main` with: `ci / lint`, `ci / unit`, `ci / secret-scan`, `eval-gate / golden-set`.
3. Settings → Secrets: `GOVERNANCE_WEBHOOK_URL`, `GOVERNANCE_WEBHOOK_TOKEN`, ingestion secrets.
4. Developers: `pip install pre-commit && pre-commit install`

Promote a SHA: Actions → **promote** → Run workflow → pick `staging` or `production`.
GitHub pauses the job until environment reviewers approve.
