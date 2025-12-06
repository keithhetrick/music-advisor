# Operator Guide: MusicAdvisor Audio Tools

## Prereqs

- Python 3.11
- Repo venv installed: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.lock`
- Required data:
  - `data/spine/spine_core_tracks_v1.csv` (for YEAR_MAX auto-detection; otherwise defaults to 2020)
  - `data/historical_echo/historical_echo.db` (optional: enables tier2/tier3 echo)
  - Calibration JSONs in `calibration/`
- Optional tempo backends: madmom/essentia (else falls back to librosa)
- Sidecar preflight: keep `scripts/check_sidecar_deps.sh` present and executable; tests enforce this guardrail.

## Environment

- Ensure repo root and `src/` on PYTHONPATH (Automators/scripts already export):  
  `export PYTHONPATH=$REPO:$REPO/src:$PYTHONPATH`
- Pinned deps enforced at runtime: numpy 1.26.4, scipy 1.11.4, librosa 0.10.1
- Sensitive values: set `LOG_REDACT=1` to mask paths/values in logs.

## Automators

- Extraction (Automator #1): `./automator.sh AUDIO1 [AUDIO2 ...]`
- HCI/client builder (Automator #2): `scripts/ma_hci_builder.sh TRACK_DIR`
- Honors `ECHO_TIERS`, `CORE_PATH`, `YEAR_MAX`, `SKIP_CLIENT`, `DRY_RUN`

## CI/Smokes

- Quick smoke: `make ci-smoke` (generates tone, runs end-to-end, writes `run_summary.json`)
- Manual smoke on your audio: `make hci-smoke AUDIO=/path/to/audio`
- Lint/tests: `make lint`, `make test`

## Common issues

- Missing CORE_PATH: ensure `data/spine/spine_core_tracks_v1.csv` exists; otherwise YEAR_MAX defaults to 2020.
- Pinned deps mismatch: rerun `source .venv/bin/activate && pip install -r requirements.lock`
- Librosa short-signal warnings: mitigated via padding; informational only.
- Optional madmom missing: sidecar falls back to librosa; install if you need Essentia/Madmom.

## Outputs

- Features: `*.features.json`, sidecar `*.sidecar.json`
- Merged: `*.merged.json` (stable schema)
- HCI: `*.hci.json` (with feature_pipeline_meta, historical_echo_v1/meta)
- Client rich: `*.client.rich.txt`
- Neighbors: `*.neighbors.json`
- Run summary: `run_summary.json` in the track folder (versions + pipeline info)
