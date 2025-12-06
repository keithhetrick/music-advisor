# Commands (Canonical)

Merged cheatsheet for day-to-day pipeline and HCI work. Replaces the older `COMMANDS.md` and `Common_CLI_Commands.md`.

## Setup

```bash
cd ~/music-advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Critical flows

- **Drag-and-drop / Quick Action (HCI-only default)**  
  `automator.sh /path/to/song.wav` → `tools/pipeline_driver.py --mode hci-only --extras --audio <file>`  
  Outputs: `<ts>.features.json`, `<ts>.sidecar.json`, `<ts>.merged.json`, `.client.*`, `.hci.json`, `.neighbors.json`, `run_summary.json` under `features_output/YYYY/MM/DD/<stem>/`.
- **Full pipeline (pack + engine audit)**  
  `tools/pipeline_driver.py --mode full --extras --audio <file> --out-dir <dir>` → adds `<ts>.pack.json` + `engine_audit.json`.
- **Audio metadata probe (read-only)**  
  `python3 -m tools.audio_metadata_probe file1.wav file2.flac` (ffprobe + mutagen, fail-soft JSON).
- **Append metadata into client rich text**  
  `python tools/append_metadata_to_client_rich.py --track-dir features_output/.../<TrackDir>`; idempotent header added to `.client.rich.txt`.

## HCI v1 maintenance

- **Compute axes for a single track (debug)**  
  `python tools/hci_axes.py --features path/to/*.features.json --market-norms calibration/market_norms_us_pop.json`
- **Recompute final scores for a date root**  
  `python tools/hci_final_score.py --root features_output/2025/11/17 --recompute`
- **Report top tracks by final score**  
  `python tools/hci_report_scores.py --root features_output/2025/11/18 --role wip --top-k 10 --sort-by final`
- **Batch recompute axes (scriptable)**  
  Use the helper loop in the archived `Common_CLI_Commands.md` to rewrite `audio_axes` across a root.
- **Rank HCI_v1 scores**  
  `python tools/hci_rank_from_folder.py --root features_output/2025/11/25 --out /tmp/hci_rank_summary.txt --csv-out /tmp/hci_rank.csv --markdown-out /tmp/hci_rank.md`

## TTC / market norms helpers

- **TTC extract (McGill)**  
  `python tools/ttc_extract_from_mcgill.py --mcgill-dir path/to/McGill/annotations --out /tmp/ttc.json --json`
- **Norms build/reporting**  
  See `docs/norms/` for snapshot build/runbooks; `docs/market_norms_*.md` moved there.

## Chat/host helpers (local)

- Merge client+HCI: `python tools/merge_client_payload.py --client <track.client.json> --hci <track.hci.json> --out /tmp/track.chat.json`
- One-shot analyze POST: `make chat-analyze CLIENT=... HCI=... [NORMS=...] [SESSION_ID=...]`
- Start stub: `make chat-stub` (file-backed) or `make chat-stub-redis` (Redis); Docker: `make chat-stub-docker`.
- Engine service: `make rec-engine-service` (POST /recommendation on port 8100; remote via `REC_ENGINE_MODE=remote`).

## Validation & debugging

- Validate artifacts: `python tools/validate_io.py --root <out_dir>` or `--file <artifact>`; schemas in `schemas/`, field refs in `docs/EXTRACT_PAYLOADS.md` and `docs/pipeline/README_ma_audio_features.md`.
- Debugging playbook: `docs/ops/DEBUGGING.md` (failure signatures, rerun patterns).
- Logs: `logs/automator_*.log` (drag/drop), `logs/pipeline_*.log` (full/engine).

## Flags and env knobs

- Profiles/timeouts: `HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS` (defaults in `ma_config/pipeline.py`).
- Sidecar: `--tempo-backend sidecar`, `--tempo-sidecar-cmd`, `--require-sidecar`; allow custom via `ALLOW_CUSTOM_SIDECAR_CMD=1`.
- Logging: `--log-json`, `LOG_JSON=1`; redaction `LOG_REDACT=1`, `LOG_REDACT_VALUES=...`; sandbox `LOG_SANDBOX=1`.
- Cache: `--cache-backend noop|disk`, `CACHE_BACKEND=...` (noop for read-only runs).
- QA: `--qa-policy default|strict|lenient`, `QA_POLICY=...` (shared across extractor/injectors/ranker).
- Automator overrides: `config/automator.env` (PATH/PY/bin/sidecar cmd/confidence bounds/clipping thresholds); `PIPELINE_DRIVER` to swap driver/mode.

## Failure signatures (triage)

- Missing `*.features.json` / `.sidecar.json`: feature or sidecar step failed (ffmpeg/sidecar deps/audio path).
- Missing `*.merged.json`: merge failed (`tools/equilibrium_merge.py`).
- Missing client/pack: `pack_writer` failed.
- Missing `engine_audit.json` / `.client.rich.txt` / `.hci.json` / `.neighbors.json`: engine or HCI builder failed.

Archived originals: see `docs/archive/ops/` if you need the full legacy text.
