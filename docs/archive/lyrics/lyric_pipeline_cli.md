# Lyric Pipeline CLI Quickstart

End-to-end examples for WIP ingestion, TTC, and neighbors.

## STT + Features + LCI export (WIP)

```bash
scripts/run_lyric_stt_sidecar.sh \
  --audio /path/to/wip.wav \
  --song-id my_wip_id \
  --title "My WIP" --artist "Me" --year 2024 \
  --db data/lyric_intel/lyric_intel.db \
  --out features_output/lyrics/my_wip_id.json \
  --lci-calibration calibration/lci_calibration_us_pop_v1.json \
  --no-vocal-separation
```

- Writes lyrics + features + vector + LCI to SQLite, emits bridge JSON (no raw lyrics).
- Use `--skip-lci` to bypass LCI; use `--transcript-file` or `--segments-file` to skip STT.

## TTC sidecar (rule-based v1)

```bash
python tools/ttc_sidecar.py estimate \
  --db data/lyric_intel/lyric_intel.db \
  --song-id my_wip_id \
  --section-pattern "V-P-C-V-C" \
  --out features_output/lyrics/my_wip_id.ttc.json
```

- Uses chorus position, tempo/duration (if present) to estimate TTC; writes `features_ttc` and JSON.

## Lyric neighbors (cosine similarity)

```bash
python tools/lyric_neighbors.py \
  --db data/lyric_intel/lyric_intel.db \
  --song-id my_wip_id \
  --limit 5 \
  --out features_output/lyrics/my_wip_id.neighbors.json
```

- Returns top-N similar songs using `features_song_vector`, with song metadata and similarity.

## Build LCI lane norms

```bash
python tools/lyric_lci_norms.py \
  --db data/lyric_intel/lyric_intel.db \
  --profile lci_us_pop_v1 \
  --out calibration/lci_norms_us_pop_v1.json
```

- Computes per-lane (tier + era_bucket) means/std for LCI axes/score and TTC; used for overlay z-scores in bridge payloads when available.

## Quickstart: WIP lyric analysis (one command)

```bash
scripts/run_lyric_wip_pipeline.sh \
  --audio "/path/to/wip.wav" \
  --song-id my_wip_id \
  --title "My WIP" --artist "Me" --year 2024 \
  --db data/lyric_intel/lyric_intel.db \
  --out-dir features_output/lyrics \
  --limit 15 \
  --distance cosine
```

- Runs STT -> lyric_intel -> LCI/TTC and writes `<out_dir>/my_wip_id_bridge.json`.
- Computes neighbors against the ingested corpus and writes `<out_dir>/my_wip_id_neighbors.json` (skip with `--skip-neighbors`).
- If the concreteness lexicon is missing, the engine logs a warning and sets concreteness to 0.0; provide the CSV later and rerun features for richer scores.

## Lyric WIP report helper

Render a quick human-friendly summary (LCI axes, TTC, neighbors):

```bash
python -m tools.lyric_wip_report \
  --bridge features_output/lyrics/<song_id>_bridge.json \
  --neighbors features_output/lyrics/<song_id>_neighbors.json \
  --norms calibration/lci_norms_us_pop_v1.json \
  --top-k 10
```

## Re-bake + WIP checklist

1. Recompute features (phase 2+3):

```bash
python -m tools.lyric_intel_engine phase2-features --db data/lyric_intel/lyric_intel.db --concreteness-lexicon data/external/concreteness/brysbaert_concreteness_lexicon.csv
```

2. Rescore LCI:

```bash
python -m tools.lci_index_builder score-songs --db data/lyric_intel/lyric_intel.db --calibration calibration/lci_calibration_us_pop_v1.json --profile lci_us_pop_v1
```

3. Rebuild norms:

```bash
python -m tools.lyric_lci_norms --db data/lyric_intel/lyric_intel.db --profile lci_us_pop_v1 --out calibration/lci_norms_us_pop_v1.json
```

4. Run WIP pipeline and report:

```bash
scripts/run_lyric_wip_pipeline.sh --audio /path/to/wip.wav --song-id my_wip --title "Title" --artist "Artist" --year 2024 --db data/lyric_intel/lyric_intel.db --out-dir features_output/lyrics --limit 15 --distance cosine
python -m tools.lyric_wip_report --bridge features_output/lyrics/my_wip_bridge.json --neighbors features_output/lyrics/my_wip_neighbors.json --norms calibration/lci_norms_us_pop_v1.json --top-k 10 --lane-era 2015_2024
```
