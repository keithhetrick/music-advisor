# Where to look (quick map)

- `README.md`: install, smoke, common failures/fixes.
- `Docs/README_Smoke_Checklist.md`: step-by-step smoke + errors.
- `Examples/`: sample payloads/packs (+ manifest with checksums).
- `QA/`: fixtures, expected ranges (`QA/ExpectedRanges_v1.json`), runbook.
- `HitCheck/`: config, synthetic cohort, README for smoketest.
- `Data/`: manifest + fetch script (external data placeholders); minimal needed: norms/baseline + bundled synthetic HitCheck cohort.
- Constraints/reqs: see `constraints.txt`, `requirements.txt`, `requirements-dev.txt`. Make targets: `make test-smoke`, `make hitcheck-smoke`, `make lint`.
- Other docs:
  - `PROJECT_OVERVIEW.md`: higher-level context.
  - `ARCHITECTURE_NOTES.md`: internals.
  - `DEPLOYMENT_GUIDE.md`: packaging/deploy steps.
  - `RELEASE_CHECKLIST.md`: release hygiene.
  - `usage_snippets.md`: quick command examples.
