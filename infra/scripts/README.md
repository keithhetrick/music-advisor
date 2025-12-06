# Infra scripts: data bootstrap & sync

- `data_manifest.json` — allowlist of S3/HTTPS assets that should land in `data/public/...`. Only put public/sanitized files here.
- `data_bootstrap.py` — downloads assets from the manifest, verifies SHA256 if provided, and writes to `MA_DATA_ROOT/public/...` (default: `data/public/...`). Never touches `data/private` or `data/features_output`.
- `data_sync_public.sh` — convenience wrapper to sync **only** `data/public` to the bucket/prefix you choose. No `--delete` by default; adjust the BUCKET/PREFIX envs if needed.

Usage:

```bash
python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
# Update S3 (shareable assets only):
BUCKET=music-advisor-data-external-database-resources PREFIX=v1/data/public infra/scripts/data_sync_public.sh
```

Notes:

- `MA_DATA_ROOT` can relocate the data root; all helpers resolve from it.
- Calibration ships in `shared/calibration/` and is not fetched from S3.
- For include-only release publishing (dated + current pointers), see `docs/ops/aws_sync.md`.
