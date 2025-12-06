# Modularity & Adapter Map

This repository uses adapter/registry shims to keep components swappable and loosely coupled.

At a glance:

```ascii
CLI/Automator -> adapters (cli/logging/time/config/qa/backend/neighbor/sidecar) -> tools/pipelines
                                         |
                                   registries/config
```

- **Sidecar adapter (`tools/sidecar_adapter.py`)**
  - Bridge for external tempo/key providers (Essentia, Madmom, etc.).
  - Swappable via backend registry; CLI flags stay stable.
- **CLI adapters (`adapters/cli_adapter.py`)**
  - Shared flags for log sandboxing and QA policy selection.
  - Ensures Automator/CLI tools expose a consistent surface.
- **Time adapter (`adapters/time_adapter.py`)**
  - Single helper for UTC timestamps to keep logs/docs consistent.
- **Config adapter (`adapters/config_adapter.py`)**
  - Resolve config precedence (CLI > env > default) and overlay helpers.
- **QA policy adapter (`adapters/qa_policy_adapter.py`)**
  - Loads QA presets and applies optional config overrides; keeps policy swaps code-free.
- **Backend registry (`adapters/backend_registry_adapter.py`)**
  - Central place to register/inspect available backends (e.g., sidecar tempo backends).
- **Logging adapter (`adapters/logging_adapter.py`)**
  - Uniform redaction/sandboxing across tools.
- **Neighbor adapter (`adapters/neighbor_adapter.py`)**
  - Controls inline-vs-external neighbor payloads and trims large lists into `neighbors.json`.

**Swap points (examples):**

- Change tempo backend: update registry/sidecar adapter without touching callers.
- Change QA defaults: adjust QA policy adapter or env; tools honor the same flag.
- Change timestamp/log format: update time/log adapters; consumers inherit behavior.
- Change neighbors payload shape: adjust neighbor adapter thresholds without touching injectors.

## Swapping components (playbook)

- **Tempo/key backends:** Register a backend in the registry; point `--tempo-backend`/sidecar command to it. Callers stay untouched.
- **QA policy tuning:** Edit `config/qa_policy.json` or use `--qa-policy`; the adapter merges overrides automatically.
- **Logging/time/CLI:** Use `logging_adapter.make_logger`, `time_adapter.utc_now_iso`, and CLI helpers when adding new tools.
- **Neighbors:** Keep top-N inline and push the rest to `neighbors.json` via the neighbor adapter.

## How adapters show up in artifacts

- Sidecar adapter → `feature_pipeline_meta.tempo_backend_detail` and `sidecar_status` in `features.json`/`merged.json`.
- QA policy adapter → QA flags and thresholds in `run_summary.json`/rich headers.
- Neighbor adapter → splits inline vs `neighbors.json` (counts/filters in `meta`).
- Config adapter → `config_fingerprint` in packs/engine audits/run summaries.
- Logging/time adapters → consistent timestamps and redacted logs across tools.

## Current coverage snapshot

- Adapters in use: extractor, injectors, ranker (QA policy adapter), sidecar runner, philosophy injectors, client/HCI merge, client payload builder, pack helpers (pack_show_hci/pack_writer), backfill reporter, common CLIs.
- Registries in use: backend registry for tempo/key; service registry for plugins.
- Known gaps: a few low-traffic utilities may still use ad-hoc CLI/logging; apply adapters there as needed for full uniformity.

This map is intended to make future refactors and backend upgrades predictable. When adding a new tool, prefer using these adapters rather than re-implementing flags or behaviors locally.
