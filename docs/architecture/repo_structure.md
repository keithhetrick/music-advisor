# Repository layout (modular overview)

This note documents the current tree so new contributors can find the right layer quickly and swap components with minimal coupling. For the monorepo plan (current vs target layout, shims, project boundaries), see `docs/monorepo/overview.md`.

- `tools/` – core scripts and automator shims
  - Pipeline/pack shims live in tools/ but canonical code is under ma_audio_engine.tools.pipeline_driver/pack_writer (see docs/COMMANDS.md).
  - `tools/cli/` – primary CLI entrypoints (use these directly in terminals/automation).
  - `tools/sidecar_adapter.py` – hardened adapter between the extractor and tempo/key sidecars (extraction sidecars/aux extractors). Overlay sidecars (tempo_norms/key_norms) are post-processing tools under `tools/`.
  - `tools/*_adapter.py` – adapter helpers; prefer importing through `adapters/__init__.py`.
  - `tools/automator_batch.sh`, `tools/audio_norm_batch.sh`, etc. – shims used by drag-and-drop Automator; keep paths stable for macOS automation.
- `adapters/` – centralized adapter layer (logging, QA policy, backend registry, JSON guards, cache/export registries). Import from `adapters` instead of individual adapter modules when possible.
- `docs/` – all documentation (moved out of repo root for clarity). Includes quickstarts, calibration notes, command references, modularity map, and architecture notes.
- `scripts/` – helper shell scripts for build/test/release that are not Automator shims.
- `schemas/`, `policies/`, `presets/` – configuration/state definitions consumed by CLIs.
- `features_output/`, `features_external/` – generated data; treat as artifacts.
- `vendor/` – nested project; **do not restructure** (kept isolated from main modular layout).
- `tests/` – test harnesses where present.

Conventions:

- Keep new CLIs under `tools/cli/` and wire Automator/macOS shims separately under `tools/`.
- When adding new helpers, expose them via `adapters/__init__.py` to preserve loose coupling.
- Avoid adding new files to repo root unless they are top-level project metadata (e.g., `README.md`, `CHANGELOG.md`).
