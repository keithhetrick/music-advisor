# Operations Whitepaper (First-Time User Guide)

Status: ✅ Last verified with Automator 11-file payload (tempo_norms sidecar + tempo overlay) and current quick-check/e2e smoke.

End-to-end, reader-first guide for installing, running, validating, and hardening the MusicAdvisor backend. Answers what each part does, how to run it, and where to look when something breaks. Use this with `docs/ops/commands.md` for quick commands.

## 1) Install & Environment

Status: current with Automator 11-file payload and quick-check/e2e smokes.

- **Python/venv:** Python 3.11. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.lock`.
- **Paths:** repo root on `PYTHONPATH` (Automator/scripts export this): `export PYTHONPATH=$REPO:$REPO/src:$PYTHONPATH`.
- **Data:** `calibration/` baselines, `data/` (spine/echo DBs), optional market norms snapshots. Sidecar deps (ffmpeg + Essentia/Madmom) improve tempo/key.
- **Guardrails:** `scripts/check_sidecar_deps.sh` must exist and be executable; CI enforces it.
- **Sensitive data:** set `LOG_REDACT=1` (mask values) and `LOG_SANDBOX=1` (scrub beats/neighbors in logs) for safer runs.

## 2) Core flows (what/why/outputs)

- **Automator / drag-and-drop (HCI-only default):** `automator.sh /path/to/audio.wav` → pipeline + echo inject. Outputs the 12-file payload under `data/features_output/YYYY/MM/DD/<stem>/`: `*.features.json`, `*.sidecar.json`, `*.tempo_norms.json`, `*.key_norms.json`, `*.merged.json`, `*.hci.json`, `*.ttc.json`, `.neighbors.json`, `.client(.json/.rich.txt/.rich.json with TEMPO + KEY overlays)`, `run_summary.json`.
- **Full pipeline (pack + engine audit):** `tools/pipeline_driver.py --mode full --extras --audio <file> --out-dir <dir>` (configure `PIPELINE_DRIVER` in Automator/macOS app). Adds `<ts>.pack.json` + `engine_audit.json`.
- **Validation:** `python tools/validate_io.py --root <out_dir>` (schemas in `schemas/`, payload refs in `docs/EXTRACT_PAYLOADS.md` + `docs/pipeline/README_ma_audio_features.md`).
- **Chat/host:** start stub via `make chat-stub` (file store) or `make chat-stub-redis`; contract in `docs/host_chat/frontend_contracts.md`.
- **Market norms:** build/report via `docs/norms/market_norms.md` (spine sync, quarter builds, host usage).
- **Lyric/TTC:** pipelines and contracts in `docs/lyrics/overview.md`.

See `docs/ops/commands.md` for copy/paste commands covering the above.

## 3) Artifacts & how to read them

- **Sidecar taxonomy (doc-only):** extraction sidecars / aux extractors (tempo/key runner writing `<stem>.sidecar.json`; lyric STT/TTC similar) read audio/primaries; overlay sidecars (tempo_norms/key_norms writing `<stem>.tempo_norms.json` / `<stem>.key_norms.json`) are post-processing on existing features/lanes. Filenames stay unchanged.
- **`*.features.json` / `*.sidecar.json`** — raw extractor + tempo/key/beat sidecar metadata (backend detail, confidence, warnings).
- **`*.merged.json`** — normalized `/audio` payload; consumed by host/rec engine.
- **`.client.*`** — legacy client helpers (text/JSON/rich); include QA + context headers.
- **`.hci.json` / `.neighbors.json`** — historical echo + neighbor results; HCI scores are diagnostics, not predictions.
- **`run_summary.json` / `engine_audit.json`** — provenance: pipeline version, config fingerprints, backend versions, degraded flags.

## 4) Debugging & failure signatures

- **Where to look:** `logs/automator_*.log` (drag/drop), `logs/pipeline_*.log` (full), stderr/stdout. Missing artifact pinpoints failing stage:
  - No `*.features.json` / `.sidecar.json`: extractor/sidecar failed (ffmpeg/sidecar deps/path).
  - No `*.merged.json`: merge (`tools/equilibrium_merge.py`) failed; schema issues.
  - No client/pack: pack writer failed.
  - No `engine_audit.json` / `.client.rich.txt` / `.hci.json` / `.neighbors.json`: engine or HCI builder failed.
- **Fast isolation:** `--skip-hci-builder` or `--skip-neighbors` to focus on extract/merge; rerun to a fresh `--out-dir` to avoid stale outputs.
- **Sidecar sanity:** ensure `.sidecar.json` exists; check `tempo_backend_detail`/`sidecar_status`; run `scripts/check_sidecar_deps.sh`.
- **Validation:** `validate_io` on the out dir; inspect `run_summary.json` for degraded flags and config fingerprints.

## 5) Robustness & provenance

- **Retries/timeouts:** bound sidecar/aux helpers; mark runs degraded on fallback; surface retry counts in `run_summary.json`.
- **Determinism:** record input audio hash, git SHA (if available), calibration version/date, library versions, random seeds; keep Trend/advisory layers separate from calibrated scores.
- **Resource controls:** small worker pool over unbounded parallelism; cap request sizes; warn on downsampling/truncation.
- **QA gates:** enforce silence/clipping/tempo-confidence thresholds; provide strict vs lenient presets (shared via `QA_POLICY`).
- **Logging/metrics:** prefer structured logs (JSONL) with correlation IDs; optional metrics exporter if you wire one later.

## 6) Testing & checks

- **Automated:** `pytest` (full); spine-only focus: `pytest tools/spine`. Host/recommendation engine: `make test`; lint/typecheck via `make lint`, `make typecheck`.
- **Smoke:** `scripts/smoke_audio_pipeline.sh /path/to/audio.wav` (extractor+sidecar); `scripts/smoke_rank_inject.sh /path/to/output_root` (injectors+ranker); `make hci-smoke` for quick HCI run; `make quick-check` (or `infra/scripts/quick_check.sh`) for fast imports/tests.
- **Manual sanity:** after backfills, spot-check row counts and random rows; run `python tools/spine/spine_coverage_report_v1.py` and `python tools/spine/report_spine_missing_audio_v1.py` for coverage.
- **Dev checks:** host/recommendation engine commands above; optional extras (Redis session, Google token verification) installed via host package extras.

## 7) Config & security quickrefs

- **Profiles/timeouts:** `HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS` (defaults `ma_config/pipeline.py`; override via `--config <json>`).
- **Sidecar:** `ALLOW_CUSTOM_SIDECAR_CMD`, `--tempo-backend sidecar`, `--require-sidecar` to fail on fallback.
- **Logging:** `LOG_JSON=1`, `LOG_REDACT=1`, `LOG_SANDBOX=1`, `LOG_REDACT_VALUES=...`.
- **Auth/sandbox:** see `docs/ops/auth_and_security.md` for host/chat auth, CORS, and sandboxing guidance.

## 8) When to escalate

- New or missing artifacts after a change → run `validate_io` and diff against prior `run_summary.json`.
- Sidecar confidence drops → reinstall deps or switch backend; rerun with `--require-sidecar` to avoid silent fallback.
- Calibration/norms changes → version baselines, update `calibration/` JSONs, re-run smokes, and refresh docs/tests that reference old paths.

If something isn’t covered here, jump to the indexed references in `docs/README.md` or the per-topic guides (architecture, host/chat, HCI, lyrics, norms, integrations).

## 9) Contributing (PR workflow basics)

- Keep changes additive; avoid breaking payload shapes or CLI flags. Update docs/tests when contracts change.
- Run `make lint` / `make typecheck` / `make test` (or narrower smoke targets) before PRs.
- If you touch paths/calibration/norms, update docs (`docs/calibration/`, `docs/norms/`) and add a note to `CHANGELOG.md` if applicable.
- For host/chat changes, keep contracts in sync with `docs/host_chat/frontend_contracts.md`; add/adjust samples in `docs/samples/`.
- For architecture moves, update `docs/architecture/repo_structure.md` and `docs/architecture/file_tree.md` as needed.

## 10) Artifacts checklist (what to verify)

- **Extractor:** `<stem>_<ts>.features.json`, `<stem>_<ts>.sidecar.json` present; `feature_pipeline_meta.sidecar_status` is `ok`.
- **Merge:** `<stem>_<ts>.merged.json` exists; schema validates; axes present.
- **Tempo norms:** `<stem>.tempo_norms.json` present; overlay injected into `.client.rich.txt` (look for TEMPO LANE OVERLAY block).
- **Key norms:** `<stem>.key_norms.json` present; overlay injected into `.client.rich.txt` (look for KEY LANE OVERLAY block).
- **Clients/HCI:** `.client.txt/.json/.rich.txt`, `.hci.json`, `.neighbors.json`, `run_summary.json` present; warnings noted.
- **Full mode extras:** `<stem>_<ts>.pack.json`, `engine_audit.json` present; audit lists all artifacts and no degraded warnings.

## 11) Artifacts gloss (what each file is for)

- `<stem>_<ts>.features.json` — raw extractor output + sidecar meta; used for merging and QA.
- `<stem>_<ts>.sidecar.json` — full tempo/key/beat payload from Essentia/Madmom; beats live here.
- `<stem>_<ts>.merged.json` — normalized `/audio` payload consumed by host/rec engine.
- `<stem>.tempo_norms.json` — lane tempo stats + advisory; feeds the TEMPO LANE OVERLAY block in `.client.rich.txt`.
- `<stem>.key_norms.json` — lane key stats + advisory; feeds the KEY LANE OVERLAY block in `.client.rich.txt`.
- `.client.txt/.json/.rich.txt` — compatibility client helpers with QA/context headers.
- `.hci.json` — historical echo diagnostic (scores + axes + neighbors summary).
- `.neighbors.json` — neighbor list (full) with metadata.
- `run_summary.json` — per-run provenance (timestamps, backends, config hash, warnings).
- `<stem>_<ts>.pack.json` — app bundle payload (merged + helpers + meta); full mode only.
- `engine_audit.json` — provenance of full run (versions, backends, artifacts); full mode only.

Schemas (JSON, draft-07): see `docs/schemas/pack_readme.md` for pack/audit/run_summary/HCI/neighbors/TTC/host response.
