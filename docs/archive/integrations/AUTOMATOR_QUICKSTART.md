# Automator / Pipeline Quickstart

Where things go and what toggles matter when using the macOS Quick Action or CLI wrappers.

## Paths & Outputs

- Output root (analysis folders): `features_output/` (configurable via `config/pipeline.env` `OUTPUT_ROOT`).
- Quick Action & drag-and-drop now share the same pipeline driver (`tools/pipeline_driver.py`) in `hci-only --extras` mode by default:
  - Outputs: 9-file legacy set in `features_output/YYYY/MM/<stem>/` (`*.features.json`, `*.sidecar.json`, `*.merged.json`, `*.client.txt/json`, `*.client.rich.txt`, `*.hci.json`, `*.neighbors.json`, `run_summary.json`).
  - Full pipeline (macOS app/GUI): call `tools/pipeline_driver.py --mode full --extras` (or set `PIPELINE_DRIVER` in `automator.sh`) to run extract → merge → pack → engine audit → HCI/client.rich/neighbors for drag-and-drop apps.
- Logs: `logs/automator_*.log` (Automator) and `logs/pipeline_*.log` (engine when applicable).
- Venv: auto-uses `.venv/bin/python`; PYTHONPATH set to include repo/src for imports.
- Sidecar preflight: `scripts/check_sidecar_deps.sh` is executed under the repo venv; tests enforce its presence/executability.
- Pipeline config: defaults live in `ma_config/pipeline.py` and can be overridden via env or `pipeline_driver.py --config <json>` (profiles/timeouts). See `docs/pipeline/PIPELINE_DRIVER.md` for modes/outputs/overrides.
- Driver flags: `--skip-hci-builder` (skip HCI/client.rich/neighbors) and `--skip-neighbors` (sets `SKIP_CLIENT=1` for the builder) for faster dev runs. Use `--mode full` in GUI contexts when you need pack + engine audit + HCI artifacts in one drag-and-drop action.

## Common Env Toggles

- `ECHO_TIERS`: auto-detected tiers if tables exist; set to `tier1_modern` to force Tier 1 only.
- `SKIP_CLIENT=1`: skip client merge/echo steps in the builder.
- `HCI_BUILDER_PROFILE` / `NEIGHBORS_PROFILE`: override defaults (`ma_config/pipeline.py`).
- `SIDECAR_TIMEOUT_SECONDS`: default 300 (override if needed).
- Notifications: `NOTIFY=1` (default) in `config/pipeline.env`.

## Usage (CLI sanity checks)

- Wrapper test (Quick Action path):  
  `cd ~/music-advisor && /bin/bash automator.sh /path/to/audio.wav`
- Check logs: `ls logs | tail` and `tail -f logs/automator_*.log`
- Output folders: `features_output/YYYY/MM/<stem>/`

## Troubleshooting

- No log created: Automator may be pointing to a different repo path; ensure it calls this repo’s `automator.sh` (or the pipeline driver directly).
- Slow writes: Finder may lag; watch the log to confirm progress.
- Missing venv: create/activate `.venv` and install deps (`pip install -r requirements.txt`).\*\*\*
