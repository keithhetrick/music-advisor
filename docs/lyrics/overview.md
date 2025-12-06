# Lyric Intelligence (First-Time Guide)

How the lyric subsystem works, how to run it, and what the outputs look like. Combines pipeline CLI, bundle contract, and reporting guidance.

## What it is

- **Goal:** turn lyrics/WIPs into stable JSON bundles with LCI scores, TTC estimates, and neighbors for downstream host/clients.
- **Inputs:** audio (for STT) or supplied transcripts/segments; calibration JSONs for LCI; lyric DB (`data/lyric_intel/lyric_intel.db`).
- **Outputs:** SQLite rows + JSON bundles (`*.ttc.json`, `*.neighbors.json`, bundle contract) without raw lyrics in the JSON.

## Run the pipeline (WIP ingest + LCI)

```bash
infra/scripts/run_lyric_stt_sidecar.sh \
  --audio /path/to/wip.wav \
  --song-id my_wip_id \
  --title "My WIP" --artist "Me" --year 2024 \
  --db data/lyric_intel/lyric_intel.db \
  --out features_output/lyrics/my_wip_id.json \
  --lci-calibration calibration/lci_calibration_us_pop_v1.json \
  --no-vocal-separation
```

- Writes lyrics + features + vector + LCI to SQLite; emits bridge JSON (no raw lyrics).
- Shortcuts: `--skip-lci`, `--transcript-file`, or `--segments-file` to bypass STT.

## TTC sidecar (rule-based v1)

```bash
python tools/ttc_sidecar.py estimate \
  --db data/lyric_intel/lyric_intel.db \
  --song-id my_wip_id \
  --section-pattern "V-P-C-V-C" \
  --out features_output/lyrics/my_wip_id.ttc.json
```

Uses chorus position + tempo/duration to estimate TTC; writes `features_ttc` and JSON.

## Lyric neighbors (similarity)

```bash
python tools/lyric_neighbors.py \
  --db data/lyric_intel/lyric_intel.db \
  --song-id my_wip_id \
  --limit 5 \
  --out features_output/lyrics/my_wip_id.neighbors.json
```

Cosine similarity over lyric vectors; `--limit` controls output size.

## Bundle contract (what clients receive)

Shape (truncated):

```json
{
  "song_id": "...",
  "title": "...",
  "artist": "...",
  "lane": {"tier": "WIP", "era_bucket": "2015_2024"},
  "lci": {
    "score": 0.72,
    "raw": 0.74,
    "calibration_profile": "lci_us_pop_v1",
    "axes": {...},
    "percentiles": {...}
  },
  "ttc": {
    "ttc_seconds_first_chorus": null,
    "ttc_bar_position_first_chorus": null,
    "estimation_method": "ttc_rule_based_v1",
    "profile": "ttc_us_pop_v1"
  },
  "neighbors": [...],
  "ingest_meta": {...}
}
```

- Axes include structure_fit, prosody_ttc_fit, rhyme_texture_fit, diction_style_fit, pov_fit, theme_fit with percentiles.
- TTC block includes estimation method/profile; neighbors block is optional and size-limited.

### Annotated bundle fields (common keys)

- `lane.tier` / `lane.era_bucket` — cohort metadata for the WIP.
- `lci.score` / `lci.raw` / `lci.calibration_profile` — calibrated vs raw lyric index and the calibration set used.
- `lci.axes` / `lci.percentiles` — six-axis breakdown (structure/prosody/rhyme/diction/pov/theme) with percentiles.
- `ttc.*` — chorus timing estimates plus method/profile; `ttc_seconds_first_chorus` is the primary signal.
- `neighbors` — lyric similarity list (size-limited).
- `ingest_meta` — provenance; use to trace calibration/ingest versions.

## Reporting / guideposts

- Use `.ttc.json` and `.neighbors.json` alongside the bundle to guide review.
- For WIP reports: surface the LCI axes/percentiles, TTC estimate, and top neighbors in the client UI (no raw lyrics in JSON).

Archived detailed docs (`lyric_intel_engine.md`, `lyric_pipeline_cli.md`, `lyric_wip_bundle_contract.md`, `lyric_wip_report_guide.md`) live in `docs/archive/lyrics/` if you need the full originals.
