# Historical Spine & Echo Tiers (Spine v1)

This folder contains tools for building the **Billboard-only Historical Spine**
used by Music Advisor's Historical Echo and HCI calibration layers.

Main entry point:

- `build_historical_spine_v1.py` — builds a rank-banded hit spine and joins in
  Spotify-style audio features from `data/external/tracks.csv`.

## Outputs

Paths are env-aware via `ma_config`: set `MA_SPINE_ROOT` and `MA_EXTERNAL_DATA_ROOT` to relocate inputs/outputs without code edits (defaults: `<repo>/data/spine`, `<repo>/data/external`).

By default the script writes to `data/spine/` (or `MA_SPINE_ROOT`):

- `spine_core_tracks_v1.csv` — one row per Billboard Year-End track (rank ≤ 200),
  including `echo_tier`, `spine_track_id`, and optional `kaggle_track_id`.
- `spine_audio_spotify_v1.csv` — audio features for tracks matched to Kaggle.
- `spine_unmatched_billboard_v1.csv` — Year-End rows with no Kaggle match.
- `historical_spine_build_v1_summary.txt` — stats per Echo Tier.

## How to run

From the repo root:

```bash
source .venv/bin/activate

# Narrow test window (e.g. 1985–1986)
python tools/spine/build_historical_spine_v1.py \
  --year-min 1985 \
  --year-max 1986

# Full backbone for 1985–2024
python tools/spine/build_historical_spine_v1.py \
  --year-min 1985 \
  --year-max 2024
```

Use the --version flag (e.g. v1_1) if you change matching rules or inputs.
Older spine CSVs stay as read-only history.
