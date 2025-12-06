# Market Norms – Q4 Workflow (no audio yet)

## Inputs available
- Chart spine: `data/market_norms/market_norms_billboard.db` (UT Hot 100/BB200).
- Q4 Hot 100 Top 40 export: `data/market_norms/raw/hot100_top40_2025_Q4.csv` (400 rows).
- Checklist with `status` column: `data/market_norms/raw/hot100_top40_2025_Q4_checklist.csv`.

## Steps once audio/features are available
1) Analyze tracks you have and produce engine `/audio` outputs (e.g., `*.merged.json`).
2) Convert to features CSV for norms builder:
   ```bash
   PYTHONPATH=. .venv/bin/python tools/audio_json_to_features_csv.py \
     --json-glob "features_output/**/*.merged.json" \
     --chart-csv data/market_norms/raw/hot100_top40_2025_Q4.csv \
     --out data/market_norms/raw/hot100_top40_2025_Q4_features.csv
   ```
3) Check what’s missing:
   ```bash
   python tools/missing_features_report.py \
     --chart data/market_norms/raw/hot100_top40_2025_Q4.csv \
     --features data/market_norms/raw/hot100_top40_2025_Q4_features.csv
   ```
4) Build the Q4 snapshot (once features CSV has data):
   ```bash
   CSV=data/market_norms/raw/hot100_top40_2025_Q4_features.csv \
   REGION=US TIER=Hot100Top40 VERSION=2025-Q4 \
   ./scripts/build_market_norms_quarter.sh
   ```
5) Inspect the snapshot:
   ```bash
   python tools/show_market_norms_snapshot.py --snapshot data/market_norms/US_Hot100Top40_2025-Q4.json
   ```

## Procurement tracking
- Use `data/market_norms/raw/hot100_top40_2025_Q4_checklist.csv` to mark `status`.
- You can regenerate the checklist anytime:
  ```bash
  python tools/billboard_checklist.py --csv data/market_norms/raw/hot100_top40_2025_Q4.csv
  ```

## Host/rec notes (no new audio needed)
- Host now warns if no norms snapshot is provided.
- You can point the host to any snapshot via `--norms <path>` when running `hosts/advisor_host/cli/ma_host.py`.

## At-a-glance commands
- DB coverage: `python tools/market_norms_db_report.py --db data/market_norms/market_norms_billboard.db`
- Export other slices: `python tools/export_billboard_slice.py --help`
- Make client bundle: `python tools/make_client_bundle.py --audio-json ... --recommendation ... --out ...`
