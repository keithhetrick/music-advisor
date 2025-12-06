# Market Norms (User Guide)

Single reference for building, inspecting, and using market norms snapshots. Merges the overview, Q4 runbook, and UT Billboard spine notes.

## What & why

- **Purpose:** versioned, read-only snapshots of market distributions (tempo, runtime, loudness, energy, danceability, valence, axes) that the host/recommendation engine consume.
- **Inputs:** UT Billboard research spine (SQLite DB) + features CSVs you generate from analyzed tracks (`*.merged.json` → CSV).
- **Outputs:** snapshot JSONs under `data/market_norms/` (e.g., `US_Hot100Top40_2025-Q4.json`).
- **Boundaries:** file/DB only; host/rec consume snapshots without code changes.

## Source spine (UT Billboard)

- DB: `data/market_norms/market_norms_billboard.db`, fed by UT Austin `rwd-billboard-data` (Hot 100/BB200). Config: `config/market_norms_ut_billboard.yml`.
- Sync: `./scripts/market_norms_sync_ut_billboard.sh` (or `SRC_PATH=/path/to/rwd-billboard-data ./scripts/market_norms_sync_ut_billboard.sh`).
- Query helpers: `tools/market_norms_queries.py`; export slices via `tools/export_billboard_top40.py`.

## Build a snapshot (example: Q4 Top 40)

1. Analyze tracks to produce `/audio` outputs (`*.merged.json`).
2. Convert to features CSV:

```bash
PYTHONPATH=. .venv/bin/python tools/audio_json_to_features_csv.py \
  --json-glob "features_output/**/*.merged.json" \
  --chart-csv data/market_norms/raw/hot100_top40_2025_Q4.csv \
  --out data/market_norms/raw/hot100_top40_2025_Q4_features.csv
```

3. Check missing coverage:

```bash
python tools/missing_features_report.py \
  --chart data/market_norms/raw/hot100_top40_2025_Q4.csv \
  --features data/market_norms/raw/hot100_top40_2025_Q4_features.csv
```

4. Build snapshot:

```bash
CSV=data/market_norms/raw/hot100_top40_2025_Q4_features.csv \
REGION=US TIER=Hot100Top40 VERSION=2025-Q4 \
./scripts/build_market_norms_quarter.sh
```

5. Inspect:

```bash
python tools/show_market_norms_snapshot.py \
  --snapshot data/market_norms/US_Hot100Top40_2025-Q4.json
```

## Procurement tracking

- Checklist: `data/market_norms/raw/hot100_top40_2025_Q4_checklist.csv` (regenerate with `python tools/billboard_checklist.py --csv data/market_norms/raw/hot100_top40_2025_Q4.csv`).
- Coverage: `python tools/market_norms_db_report.py --db data/market_norms/market_norms_billboard.db`.

## Host/rec usage

- Host warns if no snapshot is provided. Pass one at runtime: `--norms <path>` (e.g., to `hosts/advisor_host/cli/ma_host.py`).
- Snapshots are optional; without them, advisory is echo-only.

## Commands (at a glance)

- Export slices: `python tools/export_billboard_slice.py --help`
- Export top-40 slice (week or month):  
  `python tools/export_billboard_top40.py --db data/market_norms/market_norms_billboard.db --chart hot100 --year-month 2025 11 --out /tmp/hot100_top40_2025_11.csv`
- Convert audio JSON → features CSV: `tools/audio_json_to_features_csv.py` (see build step above)
- Missing report: `python tools/missing_features_report.py ...`
- Build quarter snapshot: `scripts/build_market_norms_quarter.sh` (env: CSV, REGION, TIER, VERSION)
- Inspect snapshot: `python tools/show_market_norms_snapshot.py --snapshot <path>`

Archived detailed runbooks: `docs/archive/norms/` (Q4 workflow, UT Billboard notes).

### Snapshot anatomy (example)

```json
{
  "region": "US",
  "tier": "Hot100Top40",
  "version": "2025-Q4",
  "last_refreshed_at": "2025-12-01T00:00:00Z",
  "tempo_bpm": { "p10": 80, "p50": 102, "p90": 130 },
  "duration_sec": { "p10": 150, "p50": 200, "p90": 260 },
  "loudness_LUFS": { "p10": -11.5, "p50": -9.0, "p90": -7.0 },
  "energy": { "p10": 0.4, "p50": 0.65, "p90": 0.9 },
  "danceability": { "p10": 0.4, "p50": 0.65, "p90": 0.9 },
  "valence": { "p10": 0.3, "p50": 0.6, "p90": 0.85 },
  "axes": {
    "TempoFit": { "p10": 0.4, "p50": 0.7, "p90": 0.95 },
    "RuntimeFit": { "p10": 0.4, "p50": 0.7, "p90": 0.95 },
    "LoudnessFit": { "p10": 0.4, "p50": 0.7, "p90": 0.95 },
    "Energy": { "p10": 0.4, "p50": 0.7, "p90": 0.95 },
    "Danceability": { "p10": 0.4, "p50": 0.7, "p90": 0.95 },
    "Valence": { "p10": 0.4, "p50": 0.7, "p90": 0.95 }
  }
}
```

- Percentiles capture distribution, not single values.
- `version` + `last_refreshed_at` act as provenance; do not overwrite in place—write new versions.

### Snapshot fields (quick reference)

- `region` / `tier` / `version` / `last_refreshed_at` — provenance and scope.
- `tempo_bpm`, `duration_sec`, `loudness_LUFS`, `energy`, `danceability`, `valence` — percentile dictionaries (`p10`..`p90`).
- `axes` — percentile dictionaries for derived fits (TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence).
- Optional additions should be additive only; keep existing keys stable for host/rec consumers.

Schema: `docs/schemas/market_norms.schema.json`.
