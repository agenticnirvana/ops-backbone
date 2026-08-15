## Summary
<!-- What changed and why. -->

## Eval gate
- [ ] Golden-set still passes locally: `MOCK_LLM=true python -m evals.run_evals` (from `agent/`)
- [ ] Thresholds in `agent/evals/run_evals.py` were not loosened without an eval-owner review

## Governance
- [ ] Pre-commit hooks pass (`./scripts/ci/local-gate.sh`)
- [ ] No secrets in the diff (`.env` stays gitignored)
- [ ] Production promotion will use four-eyes (requester ≠ approver)

## Test plan
- [ ] Unit / ruff
- [ ] Eval gate (CI check `eval-gate / golden-set`)
- [ ] Manual: Governance UI → Pipelines / Promotions
