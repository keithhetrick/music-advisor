# CI/Automation Smoke (suggested)

If you wire a simple CI or pre-commit hook, run these fast checks:

```bash
# ensure deps installed per README (requirements-dev.txt)
make lint            # pip check
make test-smoke      # music-advisor-smoke on sample payload
pytest Tests/test_examples_and_fixtures.py
pytest Tests/test_hitcheck_config.py
```

Expected:
- `make lint`: no dependency issues reported.
- `make test-smoke`: HCI_v1 present, Baseline/advisory populated.
- `test_examples_and_fixtures`: fixtures have required fields.
- `test_hitcheck_config`: HitCheck config points to synthetic cohort files.

Optional: add schema checks for payloads/packs if schemas are available.
