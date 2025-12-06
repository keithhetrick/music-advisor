# Release Guide

Lightweight checklist for tagging and publishing.

1. Prep

- `make clean`
- `make quick-check` (or `infra/scripts/test_affected.sh` for a scoped change, then full quick-check before tagging)
- `make -f docs/Makefile.sparse-smoke sparse-smoke-all`
- `make sbom` (optional but recommended; attach `docs/sbom/sbom.json` to release if used)
- `make vuln-scan` (non-blocking; review any findings)
- Update `CHANGELOG.md` with the new version and highlights.
- Bump version strings/badges if present (README or docs headers).

2. Version

- Bump version metadata where appropriate (docs/readme badges if used).
- Ensure manifests point only to public assets; no secrets or presigned URLs.

3. Tag

- `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- `git push origin vX.Y.Z`

4. Post-tag sanity

- Optionally rerun `make quick-check` on a clean clone.
- If distributing artifacts, attach only sanitized outputs (no audio/raw datasets).
