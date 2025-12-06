# Repo Architecture (current snapshot)

Packages

- `ma_config`: central paths/profiles/constants/audio/neighbors; env-aware defaults for calibration/data/DBs and policies.
- `ma_lyric_engine`: schema/ingest/features/LCI/norms/export.
- `ma_ttc_engine`: TTC heuristics and sidecar helpers.
- `ma_host`: host utilities (neighbors, song_context, contracts).
- Tools/CLIs under `tools/` and shell wrappers under `scripts/`.

Import guidance

- Prefer absolute package imports (avoid ad-hoc `sys.path` hacks).
- Shared path/profile lookups should come from `ma_config` helpers; avoid embedding repo-relative paths in tools/scripts.
- CLI modules should be importable without executing main; tests include import smoke to guard this.
- Console entrypoints (pyproject) decouple user-facing commands from file locations: e.g., `musicadvisor-lyric-wip`, `musicadvisor-lyric-stt`, `musicadvisor-ttc`, `musicadvisor-lyric-neighbors`, `musicadvisor-song-context`.
- Automator/Quick Action share a single pipeline driver (`tools/pipeline_driver.py`) in hci-only mode by default; defaults live in `ma_config.pipeline` (profiles/timeouts env-overridable).

Config/paths

- Paths/calibration/data roots resolve via `ma_config.paths` / `ma_config.audio` with env overrides (`MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`, `AUDIO_*`, `LYRIC_*`, `HCI_V2_*`, `HISTORICAL_ECHO_DB`, neighbor envs).
- Tools should default via these helpers and accept CLI overrides as needed.

Tests/guardrails

- Import smoke tests ensure key modules import cleanly.
- Path-literal heuristic discourages embedding `calibration/`/`data/` outside `ma_config`.
- Console `--help` smoke tests cover main CLIs.

Future monorepo moves

- Changing directory layout should primarily require updating `ma_config` helpers/env defaults rather than touching each tool. Console entrypoints (planned) will further decouple CLI names from file locations.
