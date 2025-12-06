# Commands (Canonical)

Merged cheatsheet for day-to-day pipeline and HCI work. Replaces the older `COMMANDS.md` and `Common_CLI_Commands.md`.

## Setup

```bash
cd ~/music-advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick commands (known-good)

- Fast check: `make quick-check` or `infra/scripts/quick_check.sh`
- Affected check: `infra/scripts/test_affected.sh` (uses git diff to run only relevant tests; falls back to `make quick-check`)
- Drag-and-drop: `automator.sh /path/to/song.wav` (12-file payload under `data/features_output/...`, adds `<stem>.tempo_norms.json` + `<stem>.key_norms.json` + TEMPO/KEY overlays in `.client.rich.txt`)
- Data bootstrap: `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`

## Critical flows (last verified: 12-file payload)

- **Drag-and-drop / Quick Action (HCI-only default)**  
  `automator.sh /path/to/song.wav` → `tools/pipeline_driver.py --mode hci-only --extras --audio <file>`  
  Outputs (12-file payload): `<ts>.features.json`, `<stem>.sidecar.json`, `<stem>.tempo_norms.json`, `<ts>.merged.json`, `<ts>.hci.json`, `<ts>.ttc.json`, `.neighbors.json`, `.client(.json/.rich.txt/.rich.json with TEMPO LANE OVERLAY)`, `run_summary.json` under `data/features_output/YYYY/MM/DD/<stem>/`.
- **Full pipeline (pack + engine audit)**  
  `tools/pipeline_driver.py --mode full --extras --audio <file> --out-dir <dir>` → adds `<ts>.pack.json` + `engine_audit.json`.
- **Audio metadata probe (read-only)**  
  `python3 -m tools.audio_metadata_probe file1.wav file2.flac` (ffprobe + mutagen, fail-soft JSON).
- **Append metadata into client rich text**  
  `python tools/append_metadata_to_client_rich.py --track-dir features_output/.../<TrackDir>`; idempotent header added to `.client.rich.txt`.
- **Sidecar naming (taxonomy, doc-only)**
  - Extraction sidecars / aux extractors: tempo/key runner (Essentia/Madmom/librosa, writes `<stem>.sidecar.json`), lyric STT sidecar, TTC sidecar — these read audio (or equivalent primaries) to produce core signals.
  - Overlay sidecars: tempo_norms/key_norms (write `<stem>.tempo_norms.json` / `<stem>.key_norms.json`) — post-processing overlays that read existing features/lanes. Filenames stay unchanged; the labels are to make roles explicit.
- **Generate tempo norms + inject tempo overlay**  
  `python3 tools/tempo_norms_sidecar.py --help` (produces `<stem>.tempo_norms.json`), then `python3 tools/ma_add_tempo_overlay_to_client_rich.py --client-rich <path/to/.client.rich.txt>` to insert the TEMPO LANE OVERLAY block (idempotent). Flags worth trying: `--adaptive-bin-width`, `--smoothing-method gaussian`, `--smoothing-sigma`, `--neighbor-steps/--neighbor-decay`, `--fold-low/--fold-high`, `--trim-lower-pct/--trim-upper-pct`. Sidecar exposes `peak_clusters`, `hit_medium_percentile_band`, neighbor `weight/step`, and lane `shape` metrics; the overlay can surface these fields. Key overlay legend: st=semitones delta; w=weight; c5=circle-of-fifths distance; tags=rationale tags (key norms payload also carries lane_shape, mode_top keys, fifths_chain, and rationale-tagged target moves).

- For host/chat layers: you can load sidecars directly with `tools.overlay_sidecar_loader.load_tempo_overlay_payload` and `load_key_overlay_payload` to get a humanized dict (no recompute) suitable for messaging/reco.
- Chat router (tempo/key/status intents): `from tools.chat import route_message, ChatSession, classify_intent, handle_intent` (package under `tools/chat/`). Non-implemented intents (neighbors/hci/ttc/qa) return a polite stub for now; dispatcher lives in `tools/chat/chat_overlay_dispatcher.py`.
- Help/legend/context: intents `help`/`legend`/`context` reply with supported commands, abbreviations, and current session state; router honors `verbose`/`summary` toggles, caches artifacts, truncates neighbor fields for chat, and supports metadata/lane summary/key targets/tempo targets/compare/why/artifacts intents alongside neighbors/HCI/TTC/QA/status, with filtering (top N, tier), keyword-scoring fallback, paraphrase hook (`tools/chat/paraphrase.py`, env `CHAT_PARAPHRASE_ENABLED`), optional intent model hook, and length clamping.

## Housekeeping

- One-shot cache cleanup: `infra/scripts/clean_caches.sh` (removes `__pycache__`, `.pyc`, tool caches, lint/test caches; leaves source untouched).
- Manual alternative: `find . -name "__pycache__" -type d -exec rm -rf {} +` and `find . -name "*.pyc" -delete`.
- Make targets: `make clean` (calls `infra/scripts/clean_caches.sh`), `make deep-clean` (runs `git clean -xfd`; set `CLEAN_FORCE=1` to skip prompt).

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

## Validation & debugging (last verified: 12-file payload)

- Validate artifacts: `python tools/validate_io.py --root <out_dir>` or `--file <artifact>`; schemas in `schemas/`, field refs in `docs/EXTRACT_PAYLOADS.md` and `docs/pipeline/README_ma_audio_features.md`.
- Debugging playbook: `docs/ops/operations.md` (failure signatures, rerun patterns, robustness, testing).
- Logs: `logs/automator_*.log` (drag/drop), `logs/pipeline_*.log` (full/engine).
- Samples: see `docs/samples/README.md` for ready-to-post chat payloads; use `make chat-analyze` or POST to `/chat`.
- Artifact map: `docs/ops/operations.md` includes a glossary; packs/audits/run summaries are explained in `docs/pipeline/PIPELINE_DRIVER.md` and `docs/pipeline/README_ma_audio_features.md`.
- Schemas: `docs/schemas/pack_readme.md` (pack/audit/run_summary/HCI/neighbors/ttc/host response); norms schema: `docs/schemas/market_norms.schema.json`. Pack/run_summary sections align with the current 12-file payload (tempo_norms sidecar + tempo overlay).

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
