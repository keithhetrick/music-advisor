# AWS S3 publish (internal)

Include-only sync commands for the public payload. Adjust `RELEASE` as needed; run from repo root.

Notes:

- `RELEASE` can be any tag (e.g., date or semver); dated prefixes are good for rollback.
- `current/` is the moving pointer; update it after pushing a dated release.
- Ensure `data/public` matches the manifest; only listed files should be included.
- Uploads use your local `data/public`; `MA_DATA_ROOT` does not affect what’s uploaded.

## Dated release

```bash
RELEASE=2025-01-07
aws s3 sync data/public "s3://music-advisor-data-external-database-resources/v1/data/public/${RELEASE}" \
  --exclude "*" \
  --include "README.md" \
  --include "market_norms/market_norms_us_pop.json" \
  --include "market_norms/market_norms_us_tier1_2024YE.json" \
  --include "market_norms/US_BillboardTop100_2025-01.json" \
  --include "spine/spine_master.csv" \
  --include "spine/spine_core_tracks_v1.csv" \
  --include "spine/spine_audio_spotify_v1.csv" \
  --include "spine/spine_audio_spotify_v1_enriched.csv" \
  --include "spine/spine_unmatched_billboard_v1.csv"
```

## Update current pointer

```bash
aws s3 sync data/public s3://music-advisor-data-external-database-resources/v1/data/public/current \
  --exclude "*" \
  --include "README.md" \
  --include "market_norms/market_norms_us_pop.json" \
  --include "market_norms/market_norms_us_tier1_2024YE.json" \
  --include "market_norms/US_BillboardTop100_2025-01.json" \
  --include "spine/spine_master.csv" \
  --include "spine/spine_core_tracks_v1.csv" \
  --include "spine/spine_audio_spotify_v1.csv" \
  --include "spine/spine_audio_spotify_v1_enriched.csv" \
  --include "spine/spine_unmatched_billboard_v1.csv"
```

These commands only upload the manifest-backed assets; nothing else in `data/public` will be pushed. Use `--dryrun` first if you want a preview. After publishing, users bootstrap via `infra/scripts/data_bootstrap.py` and build their own DBs locally.
