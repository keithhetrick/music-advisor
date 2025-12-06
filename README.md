# ⚙️ Music Advisor

Imagine checking your song against decades of proven hits and getting clear, step-by-step suggestions to compete on today’s charts. Music Advisor runs locally to extract those signals, compares them to hit DNA, and delivers actionable fixes without your song ever leaving your computer—all at the touch of a button.

If you want hit-level decisions, you usually have to choose between three bad options:

- Ship unreleased songs to opaque cloud tools and hope the NDA holds.
- Trust gut + playlists + screenshots with no way to reproduce decisions later.
- Glue together scripts, spreadsheets, and exports that break every time you change a backend.

Music Advisor is a local, feature-only toolchain that turns that mess into a repeatable, auditable workflow. Your audio never leaves your machine; only extracted features are used. Every run leaves a paper trail you can defend, and once you’ve cloned + bootstrapped data, the app runs entirely offline.

> Status: technical preview for collaborators (API and CLI may change between minor versions).  
> Current version: `v0.3.0`

---

## Network usage (local-first)

- Internet is only needed for the initial data bootstrap (`infra/scripts/data_bootstrap.py --manifest ...`).
- After cloning and bootstrapping, all processing (pipeline, sidecars, host/chat) runs locally; no audio or artifacts are sent to external services. All data stays internally by design, and no internet is needed to operate.

## Prereqs

- Python 3.11+ recommended.
- ~5–10 GB disk for data/bootstrap; more if you generate batches of outputs.
- Access to the data manifest (S3/HTTPS) for `infra/scripts/data_bootstrap.py` if you want the full experience.
- External drive friendly: you can clone and run from an external disk; create the venv on that disk and set `MA_DATA_ROOT` if you want data elsewhere.
- After the initial bootstrap, all processing and outputs stay within this app (repo or `MA_DATA_ROOT`); there are no external calls or uploads.
- Root/config overrides: set env vars (e.g., `MA_DATA_ROOT`, `MA_CALIBRATION_ROOT`) to relocate data/calibration; `ma_config` path helpers honor these across all components.
- Moving the repo: you can drag/clone to a new location; recreate the venv there and keep any env overrides (`MA_DATA_ROOT`, etc.) to point at your data.
- Automator/macOS: Automator/Quick Actions call `automator.sh`; if you move the repo, update the workflow to the new path (and set `MA_DATA_ROOT`/`MA_CALIBRATION_ROOT` there if needed).
- Symlink tip: for Automator, point a stable symlink (e.g., `~/music-advisor_current`) at your checkout and call `"$HOME/music-advisor_current/automator.sh" "$@"`; update the symlink if you move/rename the repo.

## Monorepo efficiency (targeted checkout)

- Sparse checkout lets you work on a single component (chat host, a sidecar, or one engine) without pulling everything.
- Each main component has its own `pyproject.toml`, tests, and run targets; the orchestrator (`tools/ma_orchestrator.py`) lets you run/test just that project.
- This keeps dependencies clear and reduces collisions when developing in isolation.
- Helper CLI (ma_helper) makes this fast: `ma sparse --set hosts shared tools`, `ma test <proj>`, `ma affected --base origin/main`, `ma ci-plan --matrix`, `ma watch <proj> [--hotkeys]`, and git-safe checks (`ma github-check`, pre-push/pre-commit hooks). See docs/tools/helper_cli.md for the full surface.

Example tree (high level)

```text
music-advisor/
  engines/
    audio_engine/              # ma_audio_engine package + tests
    lyrics_engine/             # ma_lyrics_engine + ma_stt_engine
    ttc_engine/                # ma_ttc_engine
    recommendation_engine/     # recommendation service + tests
  hosts/
    advisor_host_core/         # host contracts/helpers
    advisor_host/              # chat host/server
  shared/
    config/ calibration/ core/ security/ utils/
  tools/                       # sidecars, CLIs, orchestration
  infra/                       # scripts, data bootstrap, quick check
  tests/                       # integration/full-stack tests
```

## Quick links

- 📚 Docs index: `docs/README.md`
- 🧰 Commands: `docs/ops/commands.md`
- ✅ Helper self-checks: `tests/helper/self_check.py`
- 🗂️ Schemas: `docs/schemas/pack_readme.md`
- 🧪 Samples: `docs/samples/README.md`
- 💬 Host/chat contract: `docs/host_chat/frontend_contracts.md`
- 🏗️ Architecture overview: `docs/architecture/README.md`
- 🧵 Isolation/headless smokes: `docs/COMMANDS.md` + `docs/Makefile.sparse-smoke` (chat/sidecars/engines can be run in isolation after sparse pulls).
- 🔒 Privacy: _once cloned and data bootstrapped, everything runs locally; no audio or artifacts leave your machine - EVER._
- 🚧 Troubleshooting bootstrap: if downloads/build deps are blocked, rerun installs with `--no-build-isolation` (see Makefile/Taskfile) and ensure you can reach the data manifest URLs.

## Root essentials (what to look at first)

- Top-level files: `README.md` (this), `Makefile`/`Taskfile.yml` (bootstrap/commands), `CHANGELOG.md`, `LICENSE`, `SECURITY.md`.
- Helper entry: `ma` → `python -m ma_helper` (see `docs/tools/helper_cli.md`).
- Core dirs: `docs/`, `infra/`, `tools/`, `engines/`, `hosts/`, `shared/`, `tests/`, `ma_helper/`.
- Data/logs/caches stay ignored under `data/`, `logs/`, `.ma_cache/` (helper state defaults to `MA_HELPER_HOME` outside the repo).
- 💾 External storage: cloning/running from an external drive is fine; keep the venv on that drive and use `MA_DATA_ROOT` to point data elsewhere if desired.

## Clone → bootstrap → (optional) sparse → smoke

```bash
git clone --filter=blob:none <repo-url> music-advisor
cd music-advisor

# One-shot bootstrap (venv + deps + data + smoke)
# Recommended (pinned): uses requirements.lock
make bootstrap-locked      # or: task bootstrap-locked
# Fallback (unpinned): make bootstrap-all
# If downloads/build deps are blocked, rerun the installs with --no-build-isolation (see Makefile/Taskfile).

# Optional: sparse checkout for targeted work
git sparse-checkout init --cone
git sparse-checkout set hosts/advisor_host tools/chat tools/sidecars tools ma_config shared engines/recommendation_engine engines/ttc_engine engines/audio_engine engines/lyrics_engine docs

# Optional: install just the sparse targets if you skipped bootstrap-all
pip install -e src/ma_config -e shared -e hosts/advisor_host -e tools/chat

# Headless smokes (PYTHONPATH=. assumed)
make -f docs/Makefile.sparse-smoke sparse-smoke-all
# or per-component smokes (see docs/COMMANDS.md)
```

`make bootstrap-all` creates `.venv`, installs all projects (editable), fetches data via `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` (requires network/manifest access), and runs `infra/scripts/quick_check.sh`.
After this one-time setup, you can operate fully offline; pipeline/host/sidecars keep all processing on your machine.
If you previously installed from an older path (e.g., `MusicAdvisor_AudioTools`) and want to refresh the environment, `make rebuild-venv` will remove `.venv` (with a prompt) and recreate it via `bootstrap-all`.

## Getting started in a few minutes

1. Clone + bootstrap: `git clone … && cd music-advisor && make bootstrap-all`
2. Run chat stub: `make chat-stub` (file store; port 8090).
3. POST a sample: `curl -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d @docs/samples/chat_analyze_sample.json`
4. Explore: list projects/tests with `python3 tools/ma_orchestrator.py list-projects`; see docs links above for deeper dives.
5. Next step: run `python -m ma_helper help` (or `ma help` if you set `alias ma="python -m ma_helper"`) to see the helper commands. For a 30-second orientation, try `ma quickstart`. The helper is your main entrypoint for tasks, tests, affected runs, git/CI checks, and dashboards.
6. Optional UX dependencies: install `rich` for TUI/live dashboards and `prompt_toolkit` for fuzzy prompts. `tmux` is used by `ma chat-dev` if available (falls back to printed commands). Git helpers require running inside the repo with `.git` present.

## Open source notices

- Root `NOTICE` and MIT LICENSE files (including `src/ma_config/` and `shared/`) should be included in any redistributions. If you bundle an app, include an “Open Source Notices” section that references these.

Component READMEs (per-folder install/smoke/test):

- Chat backend: `tools/chat/README.md`
- Sidecars: `tools/sidecars/README.md`
- Pipeline quickstart: `docs/pipeline/README.md`
- Engines: `engines/*/README.md`

## Music Advisor at a glance

Creative and A&R teams make high-stakes calls on unreleased music using gut, playlists, and screenshots from black-box tools that can’t be reproduced, audited, or safely used with NDA material.

- **Who it’s for:** A&R, producers, writers, ops, and research teams who need NDA-safe, explainable analysis and ranking with hard guardrails around tempo, QA, and provenance.
- **What it gives you:** A local pipeline to extract audio features (tempo/key/mode/loudness/axes), inject historical-echo/context into client + HCI artifacts, and rank tracks with QA + tempo-confidence guardrails. Optional sidecars improve tempo/key quality.
- **Why it matters (problems → solution):**
  - **Problem 1 – NDA & trust:** Most tools demand your audio and hide their logic; you can’t safely send WIPs or explain a score later.
    **Music Advisor:** Runs 100% locally, feature-only. Audio never leaves your machine; artifacts are schema-checked and versioned so you can trace _how_ a score was produced.
  - **Problem 2 – Opaque scoring:** You get a single “magic number” with no context, no confidence, and no way to debug wrong tempos/keys.
    **Music Advisor:** Records QA gates, tempo backend details, sidecar status, and confidence flags in every output, so you can see when to trust a score—and when to rerun or reject it.
  - **Problem 3 – Irreproducible batches:** Rankings change with every tool update, playlist shuffle, or spreadsheet tweak.
    **Music Advisor:** Uses stable pipelines, config fingerprints, and cached runs so the _same_ audio + config always yields the _same_ artifacts and rankings, across projects and time.
- **How:**
  1. Extract features via Automator or `tools/cli/ma_audio_features.py`.
  2. Inject historical echo/HCI/client rich text via `tools/cli/ma_add_echo_to_*`.
  3. Rank songs via `tools/cli/hci_rank_from_folder.py` or guardrail scripts.
     Metadata records QA gates, tempo confidence, backend provenance, cache/sidecar status.
- **Sidecar taxonomy (doc-only):** extraction sidecars / aux extractors (tempo/key runner writing `<stem>.sidecar.json`; lyric STT/TTC similar, read audio/primaries) vs. overlay sidecars (tempo_norms/key_norms writing `<stem>.tempo_norms.json` / `<stem>.key_norms.json`; post-processing on existing features/lanes). Filenames stay unchanged; this label is to keep roles clear.
- **Where to start:**
  - Pipelines: `docs/pipeline/README_ma_audio_features.md`
  - Tempo/key sidecars: `docs/calibration/sidecar_tempo_key.md`
  - Ops/commands: `docs/ops/commands.md`
  - Calibration and norms: `docs/calibration/`
    Check outputs for `tempo_backend_detail`, `sidecar_status`, `qa_gate`, and config fingerprints.
- **When to use it:**
  - Any local extraction/ranking run on sensitive or unreleased audio.
  - When you want tempo/key backed by sidecars instead of guessing.
  - When you need stricter guardrails: use `--use-tempo-confidence`, QA flags, or `--require-sidecar` to fail on weak data.
  - Rerun with `--force` or `--no-cache` when changing backends/configs and you need fresh artifacts.

## Key capabilities

- 🔒 Local-only, feature-only processing; no audio uploads; confidential by design.
- 📦 Shape-stable artifacts: features, merged `/audio`, client/HCI helpers, pack/audit, run summary.
- 🛡️ Guardrails: QA policies, tempo confidence, sidecar provenance, config fingerprints.
- 💬 Host/chat ready: UI hints, quick actions, norms badges, session state; stub for local POST testing.
- ✅ Schemas for validation: pack, audit, run_summary, HCI, neighbors, TTC, host response, market norms.
- 📴 Offline-friendly after bootstrap: clone + data fetch once; everything else runs locally.

## Higher-level architecture & host/chat behavior

- Layered overview (audio engine → norms → recommendation → host/chat): `docs/architecture/README.md`
- Host/chat behavior (stateful, paging, quick actions, norms metadata): `docs/host_chat/host_chat_behavior.md`
- Chat stub quick start: `make chat-stub` / `make chat-stub-redis`; sample POST `docs/samples/chat_analyze_sample.json`
- UI mock (text): `docs/host_chat/ui_mock/mock1.md`; schema: `docs/schemas/host_response.schema.json`

## Confidentiality & safety

- Runs entirely on your machine; only extracted features are used.
- No storage of source audio; you can save feature data without saving the song.
- Sidecars and logs support redaction/sandbox; cache can be disabled.
- Explicit config fingerprints and provenance recorded in outputs.

## Data handling (repo hygiene)

- The `data/` directory is tracked but its contents are git-ignored by default; add small docs/notes there if needed, but avoid committing raw audio, databases, or heavy exports.
- Calibration lives under `calibration/`; shared configs under `config/`; schemas under `schemas/`.
- If you must version structured datasets, prefer a small sampled slice plus a README over full dumps.
- Legacy root shims and duplicate packages have been removed/archived; use venv console scripts (now pointing at `ma_audio_engine.*`) or `python -m ma_audio_engine.pipe_cli` for the pipeline entrypoint.
- Legacy source copies now live in `archive/legacy_src/` for reference; all active code resides under `engines/`, `hosts/`, and `shared/`.
- Full-app smoke: `make e2e-app-smoke` (tone → pipeline via module entrypoint → host CLI on sample payload).
- Synthetic pipeline fixtures for reference: `tests/fixtures/pipeline_sample/` (payload → advisory → host response) with a check in `tests/test_pipeline_fixture_shapes.py`.
- Full-app smoke outputs: `infra/scripts/e2e_app_smoke.sh` creates a temp dir (e.g., `/tmp/ma_e2e_xxxx`), writes `tone.wav`, `advisory.json`, and `host_out.json` there, and deletes the temp dir on exit. Nothing is left in the repo tree.
- Infra layout: orchestration lives under `infra/scripts/` and `infra/docker/`; Make targets call these paths directly.
- Calibration assets live under `shared/calibration/`; `MA_CALIBRATION_ROOT` defaults to the new location.
- Shared utilities: `shared/utils/` exists as the utilities namespace (currently re-exporting `shared.core`) to align with the target layout.
- Data scoping: `data/` remains the base (git-ignored contents). Use `data/public/` for shareable/bootstrap assets (spine, market_norms, lyric intel if provided) and `data/private/` for local-only/sensitive/generated data. Outputs live under `data/features_output/`. Path helpers in `shared/config/paths.py` resolve through `data/` (override via `MA_DATA_ROOT` if you want to point at `data/public/`).
- CI stub: `infra/scripts/ci_local.sh` runs the full quick check; use as a local stand-in until CI is wired.
- CI workflow: `.github/workflows/ci.yml` runs the quick check on push/PR.
- TTC corpus stats helper now lives under `infra/scripts/ttc_stats_report.py` (formerly in client_audio_features/).
- Data bootstrap: `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` downloads required datasets into `data/` (fill manifest URLs/checksums). Override with your own manifest or env paths as needed.
- Data/bootstrap docs: `docs/data_bootstrap.md` spells out the data layout, S3/HTTPS bootstrap, and env overrides.
- One-line public bootstrap (fetch + build public spine DB): `infra/scripts/full_public_bootstrap.sh`

## Quick start

- **Audio pipeline**
  - `./automator.sh /path/to/song.wav`
  - Outputs: `features.json`, `sidecar.json`, `merged.json`, `.client.*`, `.hci.json`, `.neighbors.json`, `run_summary.json`
- **Host/chat demo**
  - Start stub: `make chat-stub` (file store; port 8090)
  - POST a sample: `curl -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d @docs/samples/chat_analyze_sample.json`
  - See `reply` + `ui_hints`; resend `session` on follow-ups.

## Architecture at a glance (ASCII)

```ascii
audio file
  └─ ma_audio_features.py (sidecar)  →  <ts>.features.json + <ts>.sidecar.json
       └─ equilibrium_merge.py        →  <ts>.merged.json
            └─ pack_writer.py         →  <ts>.pack.json (full) + client txt/json
                 └─ run_full_pipeline.sh (full) → engine_audit.json
                      └─ ma_hci_builder.sh      → client.rich.txt + hci.json + neighbors.json
```

## Artifacts & schemas

- Pack: `docs/schemas/pack.schema.json`
- Engine audit: `docs/schemas/engine_audit.schema.json`
- Run summary: [docs/schemas/run_summary.schema.json](docs/schemas/run_summary.schema.json)
- HCI: [docs/schemas/hci.schema.json](docs/schemas/hci.schema.json); Neighbors: [docs/schemas/neighbors.schema.json](docs/schemas/neighbors.schema.json)
- TTC annotations: [docs/schemas/ttc_annotations.schema.json](docs/schemas/ttc_annotations.schema.json)
- Host response: [docs/schemas/host_response.schema.json](docs/schemas/host_response.schema.json)
- Market norms: [docs/schemas/market_norms.schema.json](docs/schemas/market_norms.schema.json)

## UI wireframes (host/chat)

- Desktop overview: [docs/host_chat/ui_mock/macos_ma_desktop_wireframe.png](docs/host_chat/ui_mock/macos_ma_desktop_wireframe.png)
- Track detail: [docs/host_chat/ui_mock/macos_ma_track_detail_full_analysis_wireframe.png](docs/host_chat/ui_mock/macos_ma_track_detail_full_analysis_wireframe.png)
- Historical echo: [docs/host_chat/ui_mock/macos_ma_historical_echo_wireframe.png](docs/host_chat/ui_mock/macos_ma_historical_echo_wireframe.png)
- Optimization card/pagination: [docs/host_chat/ui_mock/macos_ma_optimization_card_and_pagination_wireframe.png](docs/host_chat/ui_mock/macos_ma_optimization_card_and_pagination_wireframe.png)
- Norms manager: [docs/host_chat/ui_mock/macos_ma_norms_manager_wireframe.png](docs/host_chat/ui_mock/macos_ma_norms_manager_wireframe.png)
- Onboarding/help: [docs/host_chat/ui_mock/macos_ma_first_run_onboarding_window_wireframe.png](docs/host_chat/ui_mock/macos_ma_first_run_onboarding_window_wireframe.png), [docs/host_chat/ui_mock/macos_ma_help_guided_tour_window_wireframe.png](docs/host_chat/ui_mock/macos_ma_help_guided_tour_window_wireframe.png)

## Docs map

- Pipeline + artifacts: [docs/pipeline/README_ma_audio_features.md](docs/pipeline/README_ma_audio_features.md), [docs/pipeline/PIPELINE_DRIVER.md](docs/pipeline/PIPELINE_DRIVER.md)
- HCI: [docs/hci/hci_spec.md](docs/hci/hci_spec.md)
- Host/chat: [docs/host_chat/frontend_contracts.md](docs/host_chat/frontend_contracts.md), [docs/host_chat/http_stub.md](docs/host_chat/http_stub.md), [docs/host_chat/host_response_schema.md](docs/host_chat/host_response_schema.md), [docs/host_chat/ui_mock/mock1.md](docs/host_chat/ui_mock/mock1.md)
- Norms: [docs/norms/market_norms.md](docs/norms/market_norms.md)
- Calibration/sidecar: [docs/calibration/README_CALIBRATION.md](docs/calibration/README_CALIBRATION.md), [docs/calibration/sidecar_tempo_key.md](docs/calibration/sidecar_tempo_key.md)
- Ops/runbooks: [docs/ops/operations.md](docs/ops/operations.md), [docs/ops/commands.md](docs/ops/commands.md), [docs/ops/tutorials.md](docs/ops/tutorials.md)
- Spine/TTC quickstart: [docs/ops/spine_ttc_quickstart.md](docs/ops/spine_ttc_quickstart.md)
- Architecture: [docs/architecture/README.md](docs/architecture/README.md), [docs/architecture/file_tree.md](docs/architecture/file_tree.md), [docs/architecture/modularity_map.md](docs/architecture/modularity_map.md)

## What’s inside

- Pipeline driver + Automator, sidecar adapters (Essentia/Madmom/librosa), HCI/client injectors, host/chat stub, norms/calibration helpers, schemas.
- Adapters/registries keep services swappable (QA policy, cache, logging, backend registry, plugin loader).
- Logging sandbox/redaction, QA presets, cache/noop modes, pinned deps, sidecar preflight.

## Stack (quick)

- Python 3.x for core code, CLIs, and infra scripts
- Shell scripts for orchestration (infra/scripts) and smokes
- AWS S3 for public data bootstrap (see data/public/README.md, docs/ops/aws_sync.md)
- SQLite (optional) built locally from public CSVs via infra/scripts/build_public_spine_db.py
- macOS/Linux tooling for audio sidecars (ffmpeg/libsamplerate/fftw; see Health checks)

## What’s new (v0.3.0)

- Extractor JSON always contains a `TTC` block: `{seconds, confidence, lift_db, dropped, source}` (values may be `null`).
- New CLI: `ma-extract` to run your existing `analyze()` and write a normalized JSON payload.

## Install (editable)

```bash
python -m pip install -e .
python -m pip install --no-build-isolation -r requirements.txt
```

## Public data bootstrap (one-shot)

```bash
infra/scripts/full_public_bootstrap.sh
```

This fetches the manifest-backed public assets and builds the public spine SQLite DB (overwrite enabled by default). Respects `MA_DATA_ROOT` if set. Use `--no-db` to skip the DB build or `--data-root/--manifest/--db-out` to customize paths.

## Health checks

- Venv: `source .venv/bin/activate && pip install -r requirements.lock`
- Sidecar deps: `brew install ffmpeg libsamplerate fftw` then `pip install essentia` (if missing)
- Smokes: `infra/scripts/smoke_audio_pipeline.sh /path/to/audio.wav`, `infra/scripts/smoke_rank_inject.sh /path/to/output_root`

## Guardrails & sidecars (quick)

- Sidecar backend order: Essentia → Madmom → librosa; `--require-sidecar` to hard-fail on fallback.
- QA: `QA_POLICY=strict|lenient|default`, `--clip-peak-threshold`, `--silence-ratio-threshold`, `--low-level-dbfs-threshold`.
- Logging: `LOG_SANDBOX=1`, `LOG_REDACT=1`, `LOG_REDACT_VALUES=...`.
- Validate: `python tools/validate_io.py --root <out_dir>`; schemas in `docs/schemas/`.

## CLI entry points

- `ma-audio-features` → tools/ma_audio_features.py
- `tempo-sidecar-runner` → tools/tempo_sidecar_runner.py
- `equilibrium-merge` → tools/equilibrium_merge.py
- `pack-writer` → tools/pack_writer.py
- `ma-add-echo-hci` → tools/ma_add_echo_to_hci_v1.py
- `ma-merge-client-hci` → tools/ma_merge_client_and_hci.py
- `ma-add-echo-client` → tools/hci/ma_add_echo_to_client_rich_v1.py
- Pipeline driver: `tools/pipeline_driver.py` (modes: hci-only, full, client-only; see docs)

Actual stack:

- Engines: audio (`engines/audio_engine`), lyrics/STT (`engines/lyrics_engine`), TTC (`engines/ttc_engine`), recommendation (`engines/recommendation_engine`).
- Host: advisor_host + advisor_host_core.
- Shared: config/core/security/utils/calibration.
- Tools: pipeline drivers, pack/writer/merge, echo injectors, chat CLI (`tools/*`).

---

> 🛠️ Tools: Audio Features CLI · Tempo Sidecar Runner · Equilibrium Merge CLI · Pack Writer CLI · HCI Echo Injector · Client Echo Injector · Pipeline Driver
> 📂 Infra: Data Bootstrap · Public Spine Builder · Quick Check Smoke · E2E App Smoke · CI Stub
> 📄 Docs: Ops Commands · Pipeline Overview · Host/Chat Contracts · Calibration & Sidecars · Architecture Overview
