# Spine Docs

Guides for the data spine and historical backfills.

- `WORKFLOW.md` — end-to-end spine workflow (what the spine is, how to run it, expected outputs).
- `BACKFILLS.md` — backfill process and checkpoints.

Use alongside `docs/historical_spine/` for historical echo probes/whitepapers.

## Spine at a glance

- **What it is:** canonical list of tracks (slug/year/artist/title) + lanes and backfills used by historical echo and norms.
- **Core artifacts:** `data/spine/spine_core_tracks_v1.csv`, `spine_master_v1.csv`, `spine_master_v1_lanes.csv`, backfill CSVs under `data/spine/backfill/`, overrides in `data/overrides/spine_audio_overrides_v1.csv`.
- **DB import:** lanes tables live in `data/historical_echo/historical_echo.db` (Tier 1/2; Tier 3 in plan). Probes/echo use these tables for neighbors.
- **How to work:** follow `WORKFLOW.md` to build/merge; use `BACKFILLS.md` to add new sources; run coverage/missing reports after merges.

## Key lane columns (Tier 1/2 template)

- `slug` — normalized `artist__title` spine ID.
- `year` — release year (string/nullable).
- `chart` / `source_chart` — chart name.
- `year_end_rank` — rank within the source chart.
- `echo_tier` / `tier_label` — tier identifier and display label.
- `artist` / `title` — canonical strings.
- `spotify_id` / `kaggle_track_id` — optional external IDs.
- `audio_source` / `audio_features_path` — where audio/features were sourced.
- `has_audio` — flag indicating audio availability.
- Feature columns: `tempo`, `energy`, `danceability`, `loudness`, `valence`, etc. (as available per source).
