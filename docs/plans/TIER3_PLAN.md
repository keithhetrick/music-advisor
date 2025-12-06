# Tier 3 Plan — EchoTier_3_YearEnd_Top200_Modern

Tier 3 is the new weakest echo ring:

- **Name:** `EchoTier_3_YearEnd_Top200_Modern`
- **Years:** 1985–2024
- **Ranks:** Billboard Year-End Hot 100, ranks **1–200**
- **Role:** Optional neighbor pool for `historical_echo_v1` (never an HCI_v1 calibration anchor)

## Why add Tier 3?

- Strengthens historical echo coverage with a broader, modern-but-weaker pool.
- Keeps Tier 1/2 calibration untouched; Tier 3 is strictly optional and flag-gated in probes/builders.
- Allows downstream clients to show more neighbors without diluting core tiers.

## At-a-glance flow (ASCII)

```ascii
[Year-End Top 200 CSV] --> [tier3 lanes CSV] --> [spine_master_tier3_modern_lanes_v1 table]
      |                           |                     |
      |                           +--> [audio backfill script -> audio_features_path]
      |                                                 |
      +----> probe flag (--tiers include tier3) --> historical_echo_v1 neighbors (tier3 flagged)
```

## Checklist (must-do)

- [ ] Define Tier 3 lanes table in SQLite (`spine_master_tier3_modern_lanes_v1`)
- [ ] Build script to load Year-End Top 200 → Tier 3 lanes CSV
- [ ] Audio backfill script for Tier 3 (mark `has_audio`, set `audio_features_path`)
- [ ] Wire Tier 3 into echo probe CLI/API (flag-gated; defaults unchanged)
- [ ] Extend `.hci.json` writer to include Tier 3 fields (non-breaking)
- [ ] Extend `.client.rich.txt` writer to include Tier 3 neighbors (non-breaking)
- [ ] Add diagnostics snippets for coverage + probe sanity

## Tier 2 reference points (patterns to mirror)

- **Tables:** `spine_master_tier2_modern_lanes_v1` (SQLite)
- **Core scripts:**
  - `tools/spine/build_spine_core_tracks_tier2_modern_v1.py`
  - `tools/spine/build_spine_master_tier2_modern_v1.py`
  - `tools/spine/build_spine_master_tier2_modern_lanes_v1.py`
  - `tools/spine/import_spine_master_tier2_modern_lanes_into_db_v1.py`
  - Backfills: `tools/spine/build_spine_audio_from_*_tier2_modern_v1.py`
- **Echo plumbing:**
  - Probe: `tools/hci_echo_probe_from_spine_v1.py` (`--tiers tier1_modern,tier2_modern`; dedup by `(year, slug)`)
  - HCI JSON injector: `tools/ma_add_echo_to_hci_v1.py` (summary-only block)
  - Client rich injector: `tools/hci/ma_add_echo_to_client_rich_v1.py` (embeds full `historical_echo_v1` payload + header into `.client.rich.txt`)
  - Scripted default: `scripts/ma_hci_builder.sh` auto-adds Tier 2 when the table exists.
- **Slugging:** `tools/spine/spine_slug.py::make_spine_slug` (artist\_\_title), used for dedupe and spine IDs.

### Rollout steps (recommended order)

1. Build Tier 3 lanes CSV from Year-End Top 200; load into DB table.
2. Backfill audio/features; populate `audio_features_path`, set `has_audio`.
3. Gate probe/neighbor inclusion via `--tiers tier1_modern,tier2_modern,tier3_modern` (default should remain Tier 1/2 until verified).
4. Extend injectors (HCI JSON, client rich) to include Tier 3 neighbors with clear labeling.
5. Add coverage/diagnostics snippets (counts, with/without audio, probe deltas) to ensure no regressions.

### Tier 2 lanes schema (template for Tier 3)

From `sqlite3 data/historical_echo/historical_echo.db ".schema spine_master_tier2_modern_lanes_v1"`:

```text
CREATE TABLE IF NOT EXISTS "spine_master_tier2_modern_lanes_v1" (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  "spine_track_id" TEXT,
  "slug" TEXT,
  "year" TEXT,
  "chart" TEXT,
  "year_end_rank" TEXT,
  "echo_tier" TEXT,
  "tier_label" TEXT,
  "source_chart" TEXT,
  "artist" TEXT,
  "title" TEXT,
  "billboard_source" TEXT,
  "spotify_id" TEXT,
  "notes" TEXT,
  "kaggle_track_id" TEXT,
  "acousticness" TEXT,
  "audio_source" TEXT,
  "danceability" TEXT,
  "duration_ms" TEXT,
  "energy" TEXT,
  "instrumentalness" TEXT,
  "key" TEXT,
  "liveness" TEXT,
  "loudness" TEXT,
  "mode" TEXT,
  "speechiness" TEXT,
  "tempo" TEXT,
  "time_signature" TEXT,
  "valence" TEXT,
  "has_audio" TEXT,
  "tempo_band" TEXT,
  "valence_band" TEXT,
  "energy_band" TEXT,
  "loudness_band" TEXT
);
```

## Proposed Tier 3 DB schema (additive)

- Table: `spine_master_tier3_modern_lanes_v1` (created in `data/historical_echo/historical_echo.db`)
- Columns mirror Tier 2; defaults adjusted:
  - `tier_label`: `EchoTier_3_YearEnd_Top200_Modern`
  - `source_chart`: `yearend_hot100_top200`
  - `year_end_rank`: 1–200
  - Added `audio_features_path` to track resolved local features.
  - Audio + band columns stay identical otherwise for compatibility.

Created via:

```text
sqlite3 data/historical_echo/historical_echo.db "
  CREATE TABLE IF NOT EXISTS \"spine_master_tier3_modern_lanes_v1\" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    \"spine_track_id\" TEXT,
    \"slug\" TEXT,
    \"year\" TEXT,
    \"chart\" TEXT,
    \"year_end_rank\" TEXT,
    \"echo_tier\" TEXT,
    \"tier_label\" TEXT,
    \"source_chart\" TEXT,
    \"artist\" TEXT,
    \"title\" TEXT,
    \"billboard_source\" TEXT,
    \"spotify_id\" TEXT,
    \"notes\" TEXT,
    \"kaggle_track_id\" TEXT,
    \"acousticness\" TEXT,
    \"audio_source\" TEXT,
    \"danceability\" TEXT,
    \"duration_ms\" TEXT,
    \"energy\" TEXT,
    \"instrumentalness\" TEXT,
    \"key\" TEXT,
    \"liveness\" TEXT,
    \"loudness\" TEXT,
    \"mode\" TEXT,
    \"speechiness\" TEXT,
    \"tempo\" TEXT,
    \"time_signature\" TEXT,
    \"valence\" TEXT,
    \"has_audio\" TEXT,
    \"tempo_band\" TEXT,
    \"valence_band\" TEXT,
    \"energy_band\" TEXT,
    \"loudness_band\" TEXT,
    \"audio_features_path\" TEXT
  );
"
```

## Build + backfill (to implement)

- Build lanes from Year-End Top 200 CSV(s) under `data/yearend_hot100/`:
  - Script: `tools/spine/build_spine_master_tier3_modern_lanes_v1.py`
  - Inputs: `data/yearend_hot100/yearend_hot100_top200_1985_2024.csv` (or `--csv-root` for per-year files). This Top 200 CSV is derived via points from weekly Hot 100 (`tools/spine/build_yearend_top200_from_weekly_hot100.py`), scoring = `101 - rank` per week and summing per year.
  - Output: `data/spine/spine_master_tier3_modern_lanes_v1.csv` (+ optional DB import into `spine_master_tier3_modern_lanes_v1`)
  - Example:

```text
    python tools/spine/build_spine_master_tier3_modern_lanes_v1.py \
      --input-csv data/yearend_hot100/yearend_hot100_top200_1985_2024.csv \
      --out data/spine/spine_master_tier3_modern_lanes_v1.csv \
      --db data/historical_echo/historical_echo.db --reset
```

- Audio backfill:
  - Script: `tools/historical_echo_backfill_tier3_audio.py`
  - Maps normalized artist/title → local `*.features.json`, updates audio fields, recomputes bands, sets `audio_features_path`.
  - Example:

```text
    python tools/historical_echo_backfill_tier3_audio.py \
      --db data/historical_echo/historical_echo.db \
      --features-root features_output \
      --table spine_master_tier3_modern_lanes_v1
```

- Reporting queries (total / per-year counts).

## Echo plumbing updates (planned)

- Probe: `tools/hci_echo_probe_from_spine_v1.py`
  - Tier 3 flag added: `--tiers tier1_modern,tier2_modern,tier3_modern`.
  - Tier 1/Tier 2 defaults stay unchanged.
  - Example:

```text
    python tools/hci_echo_probe_from_spine_v1.py \
      --features path/to/track.features.json \
      --tiers tier1_modern,tier2_modern,tier3_modern
```

- Writers:
  - `.hci.json`: add Tier 3 block/fields without removing existing summary keys.
  - `.client.rich.txt`: embed Tier 3 neighbors under new key (e.g., `tier3_neighbors`) and update header to mention Tier 3 when present.

## Diagnostics to keep handy (Tier 3)

```text
sqlite3 data/historical_echo/historical_echo.db "
  SELECT COUNT(*) AS total, SUM(has_audio <> 0) AS with_audio
  FROM spine_master_tier3_modern_lanes_v1;udio
  FROM spine_master_tier3_modern_lanes_v1
  GROUP BY year
  ORDER BY year;
"
```

Probe sanity (once wired):

```text
python tools/hci_echo_probe_from_spine_v1.py --features path/to/sample.features.json --tiers tier1_modern
python tools/hci_echo_probe_from_spine_v1.py --features path/to/sample.features.json --tiers tier1_modern,tier2_modern
python tools/hci_echo_probe_from_spine_v1.py --features path/to/sample.features.json --tiers tier1_modern,tier2_modern,tier3_modern
```
