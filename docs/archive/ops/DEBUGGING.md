# Debugging & Failure Modes

Operational runbook for triaging pipeline/Automator/GUI runs. Focus: fast isolation, known failure signatures, and recovery steps.

---

## Signal map (where to look)

- **Logs**
  - Automator/drag-and-drop: `logs/automator_*.log`
  - Engine/HCI: `logs/pipeline_*.log` (full mode) + console stderr/stdout
- **Artifacts**: `--out-dir` or `features_output/YYYY/MM/<stem>/` → missing file pinpoints failing step (see table below)
- **Schemas**: `tools/validate_io.py --root <out_dir>`; schemas in `schemas/`, field refs in `docs/EXTRACT_PAYLOADS.md`

---

## Missing artifact → failing step (decision table)

| Missing                                                                    | Likely failing step                  | Check / Fix                                                                                      |
| -------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `<stem>_<ts>.features.json` / `.sidecar.json`                              | Features/sidecar                     | Sidecar deps (`scripts/check_sidecar_deps.sh`), ffmpeg present, audio path exists, tempo backend |
| `<stem>_<ts>.merged.json`                                                  | Merge (`tools/equilibrium_merge.py`) | Validate features schema (`validate_io`), inspect stderr                                         |
| Client/pack files                                                          | Pack writer                          | Anchor/config inputs, stderr                                                                     |
| `engine_audit.json` / `.client.rich.txt` / `.hci.json` / `.neighbors.json` | Engine or HCI builder                | `run_full_pipeline.sh`/`ma_hci_builder.sh` stderr, pack presence                                 |

Quick isolation:

- **Skip slow stages:** `--skip-hci-builder`, `--skip-neighbors` to focus on feature/merge/pack.
- **Force fresh outputs:** driver already uses `--force --no-cache`; rerun with a clean `--out-dir` to avoid stale files.
- **Sidecar sanity:** ensure `.sidecar.json` exists; check `tempo_backend_detail`/`sidecar_status`; run `scripts/check_sidecar_deps.sh`.
- **Interpreter drift:** set `PIPELINE_PY` to `.venv/bin/python` if auto-detection is wrong.

---

## Environment knobs (fast edits)

- **Profiles/timeout:** `HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS` (defaults `ma_config/pipeline.py` or `--config` JSON)
- **Logging:** `LOG_JSON=1`, `LOG_REDACT=1`, `LOG_SANDBOX=1`
- **Sidecar:** `ALLOW_CUSTOM_SIDECAR_CMD`, `SIDECAR_TIMEOUT_SECONDS` (details in `docs/sidecar_tempo_key.md`)
- **Automator:** `config/automator.env` (PATH/PY/sidecar overrides); `PIPELINE_DRIVER` to target the correct driver/mode

---

## Validate & recover

- **Schema lint:** `python tools/validate_io.py --root <out_dir>` or `--file <artifact>`
- **Rerun commands:** see `docs/pipeline/PIPELINE_DRIVER.md` for the exact feature/merge/pack/HCI commands to replay manually
- **Preserve evidence:** keep partial outputs for diffing; rerun to a new `--out-dir` to avoid overwrites
- **Update contracts:** when adding new outputs, update tests (`tests/test_pipeline_driver_outputs.py`) and docs (`docs/pipeline/PIPELINE_DRIVER.md`) to keep naming contracts clear

---

## GUI / drag-and-drop notes

- Default: hci-only `--mode hci-only --extras` (Automator/Quick Action)
- Full pipeline (pack + engine audit): `tools/pipeline_driver.py --mode full --extras` (set `PIPELINE_DRIVER` in `automator.sh` for GUI apps)

---

## Cheat sheet

- Logs: `tail -f logs/automator_*.log`
- Validate: `python tools/validate_io.py --root <out_dir>`
- Skip HCI: `tools/pipeline_driver.py --mode hci-only --skip-hci-builder --audio ... --out-dir ...`
- Full: `tools/pipeline_driver.py --mode full --extras --audio ... --out-dir ...`
