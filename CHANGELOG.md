# Changelog

## Unreleased

- macOS app UI now fully backed by MAStyle components: alerts (`AlertBanner`), prompts (`PromptBar`), headers (`HeaderBar`/`CardHeader`), chips + palettes (`ChipRow` + `FABPopover`), and rail toggle overlay. Rail width tuned (~72.6) so “History/Chat” fit without clipping; snippets use a modern FAB+popover anchored in the chips row; prompts consolidated; legacy AlertBannerView/PromptView removed. Docs updated (docs/hosts/macos_app.md) to reflect the MAStyle-backed UI.

- Helper CLI is now safety-first and feature-complete: project-aware tasks, affected logic, caching + artifact metadata, dashboards/TUI/palette/quickstart, watch hotkeys, chat-dev layout, git helpers (branch/status/upstream/rebase/pull-check), hooks (pre-push/pre-commit), guardrails, preflight/clean-tree/safe-run enforcement, state relocation (`MA_HELPER_HOME`), artifact metadata cache, and chat-dev fallback when tmux is unavailable.
- Helper self-checks added (`tests/helper/self_check.py` + CI step) covering palette/list/preflight/ci-plan/github-check/dashboard-json/chat-dev/git-sim/state-relocation/quickstart.
- Docs updated (README + docs/tools/helper_cli.md) to spotlight the helper, optional deps (rich/prompt_toolkit/tmux), git requirements, state location, artifact metadata, and new git commands. Bootstrap echoes next steps to run `ma help`/`ma quickstart`.
- Added git convenience commands: `ma git-branch`, `ma git-status`, `ma git-upstream`, `ma git-rebase`, `ma git-pull-check`; clean-tree/preflight/safe-run enforcement toggles defaultable via env.
- Helper tmux workflow documented (live dashboard split, commands, optional config template at docs/tools/tmux.conf.sample); added `ma completion zsh|bash` to emit shell completions and made `test-all` robust in parallel/serial paths.
- Added Codex review entrypoint (`make review` / `scripts/review.sh`) to run helper github-check/preflight/verify/ci-plan.
- Added Codex optimize entrypoint (`make optimize`) for report-only lint (ruff), mypy, and CI plan.
- Added `make optimize-fix` (ruff --fix + mypy + CI plan) and CI workflow `.github/workflows/codex.yml` to mirror Codex gates in GitHub Actions.

- Key/tempo overlays: richer sidecars (lane_shape, fifths_chain, rationale-tagged targets) and legends; overlays surface new fields.
- Chat package added under `tools/chat/` with intents for tempo/key/neighbors/HCI/TTC/QA/status/metadata/lane summary/targets/compare/why/artifacts/help/legend/context, summary/verbose toggles, caching, truncated outputs, optional intent model hook, and optional paraphrase hook (env `CHAT_PARAPHRASE_ENABLED`).
- Host can delegate chat replies to the modular `tools/chat` backend via `HOST_CHAT_BACKEND_MODE` + `client_rich_path`; host stays a thin front door when disabled.
- Added `docs/engine_dynamic_knobs.md` summarizing env-based dynamic toggles across host/chat and engines (audio, lyrics/STT, recommendation, TTC) to support modular/sparse development.
- Added `docs/pipeline_dynamic_knobs.md` summarizing sidecar/pipeline env hooks (sidecar command/plugin overrides, logging, overlay flag-driven behavior, `TEMPO_NORMS_OPTS`/`KEY_NORMS_OPTS` env fallbacks).
- Added TTC env fallback (`TTC_OPTS`) for sidecar defaults (seconds-per-section/profile) and documented in engine/pipeline knobs.
- TTC engine now supports optional remote mode via `TTC_ENGINE_MODE=local|remote` and `TTC_ENGINE_URL`, falling back to local heuristic on failure.
- Added optional timeouts for tempo/key/TTC sidecars via `TEMPO_NORMS_TIMEOUT`, `KEY_NORMS_TIMEOUT`, and `TTC_TIMEOUT_SECONDS`.
- Added minimal `pyproject.toml` under `src/ma_config/` and `shared/` so `pip install -e src/ma_config -e shared` installs shared libs without PYTHONPATH hacks.
- Added per-engine “minimal smoke” commands in READMEs and `docs/Makefile.sparse-smoke` targets for headless sparse verification (chat/tempo/key/ttc/reco).
- Added `tools/chat/README.md` and expanded `tools/README.md` with sidecar/chat smokes to keep targeted pulls self-describing.
- Added per-component docs: `tools/sidecars/README.md` and `docs/pipeline/README.md`, plus doc index note for component READMEs to guide targeted pulls.
- Renamed shared package stubs to `music-advisor-config` and `music-advisor-shared` (versioned at 0.1.0) for clarity/publishability.
- Added `make install-shared` helper and CI job (`Sparse Smokes`) to run headless smokes on push/PR.
- Added MIT LICENSE files under `src/ma_config/` and `shared/` for publishability.
- Added SBOM helper/docs (`docs/sbom/README.md`, `make sbom`, `SBOM` workflow) and non-blocking pip-audit workflow (`Vulnerability Scan`) for compliance hygiene.
- Added UI-friendly open-source notice snippet (`docs/ui_open_source_notices_snippet.txt`) for embedding in app UI/legal screens.
- macOS host (SwiftUI) QoL: segmented JSON/stdout/stderr viewer, “Run defaults” button, quote-aware command parsing, per-run log at `/tmp/macos_app_cmd.log`, and helper scripts for local build/run/log reset; README updated with dependency pin guidance.
- Host/chat loaders and helpers: `overlay_sidecar_loader` for sidecars; chat summaries and dispatcher for app-tailored responses.
- Chat routing supports “details” replay, context reporting, help/legend, and artifact/status checks.
- JUCE UI demo: universal (arm64+x86_64) build, manufacturer set to Bellweather Studios (Bwsd), new CMake preset + `install_root.sh` for root AU/VST3 installs, and docs updated with targeted `pluginkit` refresh (no full cache wipe).
- JUCE UI demo QoL: Ninja preset for fast Standalone-only dev, PCH removed (ObjC/PCH issues), warnings cleaned (shadowed member, deprecated Font ctor, float-to-int), and docs updated for Ninja/Xcode split and targeted refresh.
- Monorepo cleanup: root shims removed; legacy packages archived under `archive/legacy_src/`; console scripts now point at `ma_audio_engine.*`.
- Full-app smoke added (`make e2e-app-smoke`): tone → `python -m ma_audio_engine.pipe_cli` → host CLI; temp outputs only.
- Synthetic reference fixtures added (`tests/fixtures/pipeline_sample/`) with validation test.
- Docs updated (README, docs/README.md, docs/monorepo/overview.md) for shim removal, e2e smoke, fixtures, data hygiene.
- Path guard/CLI notes retained: pipeline/pack live under `ma_audio_engine.tools.*`; sys.path hacks removed.
- Infra alignment: moved orchestration under `infra/` with compatibility symlinks.
- Calibration relocated to `shared/calibration/` (root symlink retained); `MA_CALIBRATION_ROOT` default updated.
- Data scoping: `data/` organized with spine/market_norms/lyric_intel/historical_echo/features_output subfolders; symlinks added for compatibility; path helpers remain the source of truth.
- CI stub added: `infra/scripts/ci_local.sh` runs the full quick check locally.
- Shared utilities namespace added at `shared/utils/` (re-exporting `shared.core` initially).
- Root symlinks removed; paths now resolved via `shared/config/paths.py` defaults.
- Public bootstrap UX: added `infra/scripts/full_public_bootstrap.sh` (fetch + optional spine DB build), expanded `data/public/README.md` with step-by-step/schema guidance, hardened `build_public_spine_db.py` (header validation/streaming/row counts, numeric/duplicate checks, strict/paranoid modes, WAL/ANALYZE options, logging), documented S3 publish flow in `docs/ops/aws_sync.md` (moved to docs/ops), and linked from `infra/scripts/README.md`.
- CI workflow added: `.github/workflows/ci.yml` runs quick-check on push/PR.
- TTC corpus stats helper relocated to `infra/scripts/ttc_stats_report.py` to keep root clean.
- Data bootstrap added: `infra/scripts/data_bootstrap.py` with manifest template to fetch assets into `data/`.
- macOS app: route-driven reducer state, alert banners/toasts (info/warn/error), queue persistence to Application Support (best effort), preview cache and history persistence, bounded preview search, coalesced + capped stdout/stderr updates, trimmed console log buffer, host polling backoff, lazy stacks for log/history/queue, copy-pane action, and host-architecture docs; MAStyle remains the styling source of truth.
- JUCE UI demo added under `plugins/juce_ui_demo`: custom vector controls (dials, envelope mini-view, meter), safe DSP shell, AU/VST3/Standalone via JUCE CMake; docs at `docs/juce_ui_demo.md`.
- macOS app shell overhaul: nav rail + adaptive split panes (Run/History/Console), glassy depth via MAStyle, keyboard shortcuts (run/reveal/theme, history search, console prompt), accessibility labels on key controls, missing-file guards for reveal/rerun, snippets that prefill/focus prompt, history filters with preview card (reveal/preview/rerun), onboarding overlay, non-blocking toasts with throttling, local chat stubbed reply, and `scripts/swift_run_local.sh` now opens the built .app (keyboard focus stays in window).

## v0.3.0 — 2025-11-07

- Always-present TTC block in extractor payloads via `always_present.py`.
- Added `ma-extract` CLI to run analyze() and emit shape-stable JSON.
- Added basic tests to guarantee payload schema stability.

v1.1.2 / 0.1.7 — HCI_v1 is always present (CLI & Builder), added --round in both CLI paths, stabilized TTC gate reporting.
