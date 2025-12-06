# Support

- **How to get help**: Open an issue with clear steps to reproduce and logs (redacted). For security-sensitive topics, use the private channel described in `SECURITY.md`. Primary channel: GitHub issues; for private ops, email `support@music-advisor.dev` (example).
- **What to include**: OS, Python version, command(s) run, expected vs. actual output, and any relevant files under `logs/` or `data/features_output/` (paths are fine; do not attach raw audio or private data). Include whether MA_DATA_ROOT was overridden.
- **Self-service**:
  - Quick check: `make quick-check`
  - Scoped check: `infra/scripts/test_affected.sh`
  - Clean caches: `make clean`
  - Data bootstrap: `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`
