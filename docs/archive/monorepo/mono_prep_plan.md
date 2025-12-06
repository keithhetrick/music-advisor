# Monorepo Prep Plan (Current Repo Snapshot)

Reality check (as of this snapshot)

- Packages: ma*config (paths/profiles/constants/audio/neighbors), ma_lyric_engine, ma_ttc_engine, ma_host, tools/* CLIs, scripts/\_.sh.
- Data/config roots: calibration/, data/, features_output/, scripts/ + tools/ wrappers.
- Env-aware helpers already present: ma_config.paths (data/calibration roots, lyric DB, echo DB), ma_config.audio (HCI/HCI_v2 paths, market norms, policies, corpus/targets/training CSVs, loudness norms), ma_config.neighbors (limit/distance/config), ma_config.constants (LCI axes/lanes), ma_config.profiles (profile resolution).
- Many tools now consume these helpers (lyric STT/WIP, TTC, neighbors, HCI audio v2 apply/fit/backfill, corpus/training builders, loudness fitter, echo injectors/importers, song_context builder, lyric engines).
- Residual sys.path hacks: some tools still prepend repo root for convenience; imports generally absolute within packages.

Target (within current repo; no moves yet)

- Keep file layout but enforce package imports (minimize sys.path hacks).
- Centralize remaining hard-coded paths via ma_config.locator helpers.
- Add contract/constants module for bundle/DB keys.
- Provide stable console entrypoints via pyproject for key flows.
- Add import smoke + path-lint tests; flag literal calibration/ and data/ paths.
- Document architecture, config/paths, and future monorepo blueprint.

Planned phases

- Phase 2: Import hygiene
  - Swap remaining sys.path inserts in tools to package imports where safe.
  - Add import-smoke pytest (import key tools/modules; run --help where feasible).
  - Document package boundaries in docs/repo_architecture.md (add/update).
- Phase 3: Config locator hardening
  - Extend ma_config.paths/audio for any remaining roots (features_output, external data).
  - Replace lingering hard-coded paths (e.g., in less-used scripts/guardrails) with locator/helpers.
  - Add heuristic lint/test to flag new literal “calibration/” or “data/” strings outside ma_config.
  - Document env vars and resolution order in docs/config_and_paths.md.
- Phase 4: Contract constants
  - Add ma_host/contracts.py (or similar) for bridge/bundle/song_context keys and DB table names.
  - Refactor key producers/consumers (song_context_builder, lyric bundles, exports) to use constants.
  - Add contract tests (golden schema check) for song_context/bundle shapes.
- Phase 5: Console entrypoints
  - Define console scripts in pyproject for common flows (e.g., lyric-wip, lyric-wip-pipeline, rebake-lyrics, song-context, hci-simple, hci-audio-v2-apply/fit, ttc-sidecar, lyric-neighbors).
  - Update scripts to call console entrypoints where reasonable; keep backward-compatible shims.
  - Add smoke test importing entrypoint modules and running --help.
- Phase 6: Monorepo blueprint (docs only)
  - Draft docs/monorepo_blueprint.md with proposed /apps /packages /shared layout.
  - Include migration checklist (pytest, import smoke, WIP pipeline smoke, contract checks).

Notes/constraints

- No large moves now; prep for future mono layout by tightening imports/config.
- Preserve external contracts and current CLI flags; changes should be additive.
- Keep tests green; add new lightweight tests rather than heavy end-to-end runs.
