# Architecture Overview (Canonical)

Local-first audio + lyric intelligence built around adapters, registries, and shape-stable artifacts. This merges the older overview/whitepaper snapshots into a single home. For the current + target monorepo layout (projects, shims, and move plan) see `docs/monorepo/overview.md`.

## System flow (HCI-only default)

```text
audio file
  -> ma_audio_features.py (sidecar) -> <ts>.features.json + <ts>.sidecar.json
  -> equilibrium_merge.py           -> <ts>.merged.json
  -> pack_writer.py (--no-pack)     -> client helper payloads (.client.txt/.json)
  -> ma_hci_builder.sh              -> .client.rich.txt + .hci.json + .neighbors.json + run_summary.json
```

- Full pipeline adds `run_full_pipeline.sh` → `engine_audit.json` + `<ts>.pack.json`.
- Artifacts are shape-stable (`*.features.json`, `*.sidecar.json`, `*.merged.json`, `*.pack.json`, `.client.*`, `.hci.json`, `.neighbors.json`, `run_summary.json`).
- Config defaults live in `ma_config/pipeline.py`, `ma_config/audio.py`, and adapters’ configs under `config/`; env/JSON/CLI overrides are layered on top.
- Sidecar taxonomy (doc-only): extraction sidecars / aux extractors (tempo/key runner writing `<stem>.sidecar.json`; lyric STT/TTC similar) vs. overlay sidecars (tempo_norms/key_norms writing `<stem>.tempo_norms.json` / `<stem>.key_norms.json`; post-processing on existing features/lanes). Filenames remain unchanged.

## Tiered architecture (replaceable boundaries)

- **Tier 1 — Audio Engine**: Computes `/audio` JSON (tempo, runtime, loudness, energy, danceability, valence, axes). Lives in `tools/` + adapters; outputs `*.features.json` and `*.merged.json`.
- **Market Norms spine**: Builds versioned norms snapshots from UT Billboard research and extracted features. File/DB only; no host/engine coupling.
- **Tier 2 — Recommendation/Optimization**: Consumes `/audio` + optional norms snapshot to emit recommendation JSON. Lives under `engines/recommendation_engine/...`.
- **Tier 3 — Host/Chat**: Thin FastAPI shell for session state/intent routing. Consumes recommendation outputs and optional norms snapshot; no scoring logic. Lives in `hosts/advisor_host/`.
- Optional helpers: bundle makers, coverage/missing reports, DB inspectors.

Each arrow is a file/API boundary. You can swap providers or move code without breaking consumers as long as payload shapes stay stable.

## Repo packages and import guidance

- Packages: `ma_config` (paths/profiles/constants/audio/neighbors), `ma_lyric_engine`, `ma_ttc_engine`, `ma_host`, tools/CLIs under `tools/`, shell wrappers under `scripts/`.
- Prefer package imports over ad-hoc `sys.path` edits; console entrypoints (pyproject) decouple CLI names from file locations (e.g., `musicadvisor-lyric-wip`, `musicadvisor-ttc`, `musicadvisor-lyric-neighbors`, `ma-host`).
- Paths/config come from `ma_config` helpers; avoid embedding repo-relative literals in tools/scripts.
- Tests include import smoke + path-literal heuristics to guard against regressions.

## Modularity principles

- Separation of concerns: adapters own I/O, validation, logging, and registry lookups; pipelines own orchestration.
- Least privilege: no hard-coded paths; validate sidecar commands against allowlists; enforce registries and profiles.
- Swappability: add new tempo/key engines, QA presets, caches, or backends via registries/adapters without touching business logic.
- Observability & safety: structured logs with redaction/sandboxing; schema linting; config fingerprints and sidecar status recorded in artifacts.

## Visual map (ASCII)

```ascii
[Audio file] --extract--> [features.json + sidecar.json] --merge--> [merged.json]
      |                                         |
      |                                         +--> [run_summary.json]
      +-- sidecar (tempo/key/beat)              |
                                                v
                                     [pack_writer (--no-pack|full)]
                                                |
               +------------------------------- + --------------------------+
               |                                |                          |
      [.client.txt/.json/.rich.txt]     [.hci.json + neighbors.json]   [pack.json + engine_audit.json]
               |                                |                          |
               +-----------------------------> Host/Chat <-----------------+
                                                |
                                 (optional) Market Norms snapshot
```

### Artifact map (where to look)

- Extract: `<stem>_<ts>.features.json`, `<stem>_<ts>.sidecar.json` (tempo/key/beat provenance).
- Merge: `<stem>_<ts>.merged.json` (normalized `/audio` payload for downstream).
- Pack/full mode: `<stem>_<ts>.pack.json`, `engine_audit.json` (provenance + bundle).
- Client/HCI: `.client.*`, `.hci.json`, `.neighbors.json`, `run_summary.json` (compatibility + diagnostics).
- Host/Chat: consumes merged/HCI/pack; contract in `docs/host_chat/frontend_contracts.md`.

## How to extend safely

- Register new backends/services via small adapter modules and registries.
- Keep user-facing flags in CLI wrappers; delegate work to shared helpers in `src/` or `adapters/`.
- Document new modules/flags in `docs/architecture/repo_structure.md` (and link here).
- Use `ma_config` for paths/profiles; add import-smoke + path-lint coverage when adding new tools.

## Related docs

- `docs/architecture/file_tree.md` — current tree snapshot.
- `docs/architecture/repo_structure.md` — directory/package breakdown.
- `docs/architecture/modularity_map.md`, `docs/architecture/components.md`, `docs/architecture/adapters.md` — deeper dives.
- Archived prior snapshots: `docs/archive/architecture/`.
