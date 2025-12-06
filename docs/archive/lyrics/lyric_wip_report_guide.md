# Lyric WIP Report Guide (LCI + TTC + Neighbors)

## Overview

- WIP pipeline: STT sidecar transcribes audio → Lyric Intelligence Engine computes structure/style/sentiment/rhyme/theme/prosody features → LCI (6 axes + score) using Billboard-aligned calibration → TTC heuristic estimates first chorus timing → neighbors locate similar lyric shapes in the corpus.
- Outputs: bridge JSON (lyric_intel + lyric_confidence_index + ttc_profile) and neighbors JSON (similarity list).
- Report CLI (`tools/lyric_wip_report.py`) renders a human-readable summary with percentiles and neighbors.

## LCI and axes

- Axes: `structure_fit`, `prosody_ttc_fit`, `rhyme_texture_fit`, `diction_style_fit`, `pov_fit`, `theme_fit`.
- `raw` = pre-calibration aggregation; `score` = calibrated to corpus profile (e.g., `lci_us_pop_v1`).
- Calibration profile ties to the historical cohort used for norms/calibration.
- Percentiles (`p ~ 0.xx`) come from lane norms (default honors `LYRIC_LCI_NORMS_PATH` or `calibration/lci_norms_us_pop_v1.json`).

## Lanes, norms, percentiles

- Lanes = chart tier + era buckets (e.g., Tier 1 Top 40, era 2015–2024).
- Norms JSON (e.g., `calibration/lci_norms_us_pop_v1.json`) stores mean/std per axis/score per lane.
- Percentiles shown as `p ~ 0.xx` indicate where the WIP sits relative to that lane (approximate percentile, not statistical p-value).

## TTC (Time-To-Chorus)

- `ttc_seconds_first_chorus`, `ttc_bar_position_first_chorus` from `ttc_profile`.
- Current heuristic `ttc_rule_based_v1` uses section patterns and tempo/duration when available; may be `N/A` if no clear chorus is detected.
- `ttc_confidence` (high/medium/low) indicates reliability; treat low as advisory only.

## Neighbors

- Computed from `features_song_vector` using cosine (default) or euclidean distance; shape-based, not genre-based.
- Report dedupes by (title, artist, year) for readability (one line per canonical song entry).
- Use neighbors as reference points for lyrical lane/shape echoes.

## Example (shortened)

```bash
Song: ...
Lane: tier=..., era_bucket=...
---
LCI:
  score: 0.72 (p ~ 0.86)
  raw: 0.74
  calibration_profile: lci_us_pop_v1
  Axes:
    - structure_fit: 0.96 (p ~ 0.80)
    - prosody_ttc_fit: 0.95 (p ~ 0.87)
    - rhyme_texture_fit: 0.53 (p ~ 0.56)
    - diction_style_fit: 0.81 (p ~ 0.07)
    - pov_fit: 0.99 (p ~ 0.90)
    - theme_fit: 0.17 (p ~ 0.17)
TTC:
  ttc_seconds_first_chorus: N/A
  ttc_bar_position_first_chorus: N/A
  estimation_method: ttc_rule_based_v1
  Note: No clear chorus detected.
Top neighbors:
  #1 ...
  ...
Summary:
  - Overall lyric confidence: 0.72 (~0.86 lane percentile).
  - Strong axes: structure_fit, prosody_ttc_fit, pov_fit.
  - Development axes: theme_fit.
  - TTC: No clear chorus detected by v1 heuristic.
```

## Usage

- Pipeline: `scripts/run_lyric_wip_pipeline.sh --audio ... --song-id ... --out-dir ...`
- Report: `python -m tools.lyric_wip_report --bridge <bridge.json> --neighbors <neighbors.json> --norms calibration/lci_norms_us_pop_v1.json --top-k 10` (norms default via `LYRIC_LCI_NORMS_PATH`).
- Flags: `--lane-era` to pick a reference lane for overlay, `--include-self` to show the WIP in neighbors, `--show-duplicates` to show all neighbor variants.
