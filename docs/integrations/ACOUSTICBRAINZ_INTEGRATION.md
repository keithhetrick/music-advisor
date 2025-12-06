# AcousticBrainz Integration (Tier 3 Only)

Optional, non-calibrating AcousticBrainz path that only touches Tier 3. Tier 1 / Tier 2 schemas and HCI_v1 calibration remain unchanged.

## Why/when to use this

- **Use this** when you already have a local AcousticBrainz server or dumps and want Essentia-grade features for Tier 3 spine/probes without running local Essentia/Madmom sidecars.
- **Skip it** if you prefer the default pipeline sidecar (Essentia/Madmom/librosa locally) and don’t need the ABBZ service/dumps; this integration is optional.

## Tables (SQLite: `data/historical_echo/historical_echo.db`)

- `spine_musicbrainz_map_v1`: maps `slug` → MusicBrainz recording MBID plus metadata (`title`, `artist`, `year`, `mbid_confidence`, timestamps).
- `features_external_acousticbrainz_v1`: compact AcousticBrainz scalar subset keyed by `slug` + `recording_mbid`. `features_json` stores a small JSON blob (tempo, loudness, a few mood/danceability probabilities, optional tonal hints). Indexes on `slug` and `recording_mbid`.

Create via helper (idempotent): `tools.db.acousticbrainz_schema.ensure_acousticbrainz_tables(conn)`.

## Scripts

1. **Backfill MusicBrainz MBIDs**  
   `python tools/spine/backfill_musicbrainz_mbids_for_spine_tiers.py --tiers tier3_modern --limit-per-tier 100 --dry-run`

   - Inputs spine rows (`slug,title,artist,year`), queries MusicBrainz recordings, and upserts into `spine_musicbrainz_map_v1`.
   - Respects `--force`, `--sleep-seconds`, and `--user-agent`. Default tier is `tier3_modern`.

2. **Fetch AcousticBrainz features**  
   `python tools/external/acousticbrainz_fetch_for_spine_mbids.py --tiers tier3_modern --max 200`

   - Reads MBIDs from `spine_musicbrainz_map_v1`, calls AcousticBrainz low/high level APIs, stores compact scalars in `features_external_acousticbrainz_v1`, and saves raw JSON to `features_external/acousticbrainz/`.
   - Supports `--force`, `--dry-run`, `--sleep-seconds`, and optional tier filters.
   - Offline ingest (if you have dumps):  
     `python tools/external/acousticbrainz_fetch_for_spine_mbids.py --tiers tier3_modern --offline-low-dir /path/to/lowlevel_dir --offline-high-dir /path/to/highlevel_dir --offline-only`  
     (recursive search; handles sharded dumps; `--offline-only` skips the live API)

3. **Echo probe fallback (Tier 3 only)**  
   `python tools/hci_echo_probe_from_spine_v1.py --features path/to/track.features.json --tiers tier1_modern,tier2_modern,tier3_modern --use-acousticbrainz-fallback --acousticbrainz-max-fallback 50`

   - When local Tier 3 Essentia sidecar is missing, the probe can optionally pull compact AcousticBrainz features.
   - Neighbors now include `feature_source` (`essentia_local` or `acousticbrainz`). Tier 1 / Tier 2 behavior is unchanged unless the flag is set, and HCI_v1 calibration math is untouched.

4. **Diagnostics**  
   `python tools/external/acousticbrainz_diagnostics_tier3.py --verbose`
   - Reports Tier 3 coverage (Essentia vs AcousticBrainz vs neither) and basic axis deltas where both exist.

Offline ingest (optional, if you have AcousticBrainz dumps):

- Provide directories of extracted `<MBID>.lowlevel.json` and `<MBID>.highlevel.json` files:  
  `python tools/external/acousticbrainz_fetch_for_spine_mbids.py --tiers tier3_modern --offline-low-dir /path/to/lowlevel_dir --offline-high-dir /path/to/highlevel_dir --offline-only`
- If `--offline-only` is omitted, the script will use offline files when present and fall back to the live API otherwise.

## Notes

- AcousticBrainz data is lower trust than local Essentia and is only used as a Tier 3 neighbor filler.
- Defaults preserve current behavior; enable explicitly with `--use-acousticbrainz-fallback`.
- MusicBrainz/AcousticBrainz access respects rate limits; use `--limit-per-tier` / `--max` for staged runs.
