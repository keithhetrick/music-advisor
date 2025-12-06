# TTC Discovery (sidecar v1)

Repo scan focused on TTC/structure/chorus/beat references. Highlights are grouped by area with file paths.

## Existing TTC scripts and stubs
- tools/ttc_auto_estimate.py: Librosa-based heuristic that picks the earliest strong recurrence peak; optional BPM → bars. Emits `ttc_seconds_first_chorus`, `ttc_bars_first_chorus`, `ttc_source`, `ttc_estimation_method`.
- tools/ttc_extract_from_mcgill.py: Parses McGill Billboard .txt annotations; first label containing “chorus” → `ttc_seconds`; writes CSV/JSON.
- build_ttc_corpus.py: Merges Harmonix + McGill TTC CSV/JSON, preferring Harmonix on title/artist collisions.
- tools/ttc_sidecar.py: CLI stub; loads lyric intel DB, derives section pattern/tempo, calls ma_ttc_engine.detect_choruses. Writes to `features_ttc` table if song_id provided.
- ma_ttc_engine/detect_choruses.py: Rule-based placeholder; finds first label starting with CHORUS/C; uses duration or fallback seconds-per-section; optional tempo→bars; returns `ttc_seconds_first_chorus`, `ttc_bar_position_first_chorus`, `ttc_confidence`.
- ma_ttc_engine/ttc_features.py: Stub feature builder; writes TTC into `features_ttc`.
- ma_lyric_engine/schema.py: Defines `features_ttc` table in lyric intel DB (song_id PK; seconds, bars, estimation_method, profile, ttc_confidence). No ground-truth corpus tables exist yet.

## Pipeline touchpoints
- tools/pipeline_driver.py: Prefers TTC in sidecar payload; otherwise calls tools/ttc_auto_estimate.py on audio; writes per-run `<stem>.ttc.json` merged into downstream pack.
- tools/lyric_wip_pipeline.py: Imports tools.ttc_sidecar and runs `run_estimate` with optional TTC profile/config.
- tools/builder_cli.py: Reads TTC from beatlink.json/mvp.json if present; logs optional TTC in header.
- tools/validator/verbose_validator.py: Has policy flags for TTC (`use_ttc`); can mark `ttc_sec` ignored.

## Lyric/structure helpers (potential reuse)
- lyrics/lyricflow.py, lyrics/sectionizer.py, lyrics/lyricflow_plus.py: Text-based segmentation/chorus scoring; returns sections and earliest hook exposure (`hook_first_exposure_sec`). Could inform chorus label mapping or heuristics.
- lyrics/aligners.py: Rough alignment of sections/lines to beatgrid when BPM + first beat exist.
- ma_lyric_engine/export.py, lci_norms.py, lci_overlay.py: Consume `features_ttc` when present for export/norms, but TTC is optional and gated by available rows.

## Data or metadata hints
- data/external/melody/BiMMuDa-main/...: Metadata CSVs with chorus/post-chorus labels (not currently ingested).
- tools/.ma_cache/sidecar/...: Cached tempo sidecar JSONs (beats_count) only; no TTC values observed.

## Gaps relative to TTC sidecar plan
- No dedicated TTC sidecar tables in historical echo/hci DBs.
- No multi-dataset structural parsers beyond McGill stub; Harmonix/SALAMI etc. not implemented.
- No summarization/diagnostics scripts for TTC corpus yet.
- Existing TTC logic is stubby and local to lyric intel; needs separation from HCI_v1/Tier tables per plan.
