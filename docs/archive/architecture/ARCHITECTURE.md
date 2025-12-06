# Architecture & Modularity (Whitepaper)

**Purpose:** Local-first audio + lyric analysis that emits shape-stable artifacts for scoring/ranking. The system is built around adapters/registries to keep backends swappable, policy-driven, and safe to extend.

---

## System overview

**Top-level flow (hci-only default):**

```text
audio file
  -> ma_audio_features.py (sidecar) -> <ts>.features.json + <ts>.sidecar.json
  -> equilibrium_merge.py           -> <ts>.merged.json
  -> pack_writer.py (--no-pack)     -> client helper payloads (.client.txt/.json)
  -> ma_hci_builder.sh              -> .client.rich.txt + .hci.json + .neighbors.json + run_summary.json
```

**Full pipeline:** add `run_full_pipeline.sh` → `engine_audit.json` + timestamped `.pack.json`.

**Artifacts (shape-stable):**

- Features: `<stem>_<ts>.features.json` (flat pipeline schema)
- Sidecar: `<stem>_<ts>.sidecar.json` (tempo/key/beat, backend/meta/confidence)
- Merged: `<stem>_<ts>.merged.json` (normalized schema)
- Pack (full mode): `<stem>_<ts>.pack.json`
- Compatibility copies: `<stem>.client.txt/.json/.rich.txt`, `<stem>.hci.json`, `<stem>.neighbors.json`, `run_summary.json`
- Engine audit (full): `engine_audit.json`

**Config & provenance:**

- Defaults live in `ma_config/pipeline.py`, `ma_config/audio.py`, and adapters’ configs under `config/`.
- Env/JSON/CLI overrides: profiles (`HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`), sidecar timeout, logging (LOG_JSON/LOG_REDACT/LOG_SANDBOX), cache backend, QA policy.
- Every artifact carries `pipeline_version` and config fingerprints; sidecar status/warnings recorded on fallback; `--require-sidecar` to hard-fail.

---

## Components (what they do and why)

- **Adapters (`adapters/*.py`)**: Guardrails and indirection for config, QA policy, logging/redaction/sandbox, CLI args, backend registry, cache, neighbor export, time helpers. Keep business logic out of scripts; make swaps low-touch.
- **Registries (`adapters/backend_registry_adapter.py`, `adapters/service_registry.py`)**: Discover and gate backends/services so new providers can be added without changing core tools; enforce allowlists.
- **Pipelines/Tools (`tools/*.py`)**: Orchestrators that wire adapters/registries. Key ones: `ma_audio_features.py` (extractor), `ma_add_echo_to_client_rich_v1.py`, `ma_add_echo_to_hci_v1.py`, `hci_rank_from_folder.py`, `tempo_sidecar_runner.py`, `pipeline_driver.py`.
- **Sidecar adapter (`tools/sidecar_adapter.py`)**: Safe bridge to external tempo/key backends (Essentia/Madmom/librosa). Validates command templates, enforces allowed binaries, caps JSON size, normalizes confidence, and returns warnings instead of blowing up pipelines.
- **QA/Policies (`adapters/qa_policy_adapter.py`)**: Centralized thresholds/presets to keep guardrails consistent across extractor/injectors/ranker.
- **CLI/Logging/Time adapters**: Shared option parsing, structured logging (with redaction/sandbox), and timestamp helpers to keep scripts uniform and safe in logs.
- **Docs & presets**: Calibration/tempo confidence docs live in `docs/` and `presets/`; `docs/COMMANDS.md` lists entrypoints; `docs/DEBUGGING.md` captures failure modes and reruns.

---

## Modularity principles

- **Separation of concerns:** Adapters own I/O, parsing, validation; pipelines own orchestration.
- **Least privilege:** No hard-coded paths; use `ma_config/paths` and registries; validate sidecar commands against allowlists.
- **Swappability:** New tempo/key engines or QA presets registered once; callers unchanged. Cache/logging/neighbor writers are adapterized.
- **Observability & safety:** Structured logs, redaction, sandbox scrubbing; schema linting (`tools/validate_io.py`); config fingerprints and sidecar status recorded in artifacts.

---

## How to extend safely

1. Add/adjust an adapter instead of inlining logic in tools (config, QA, logging, cache, neighbor, backend registry).
2. Register new backends in `backend_registry_adapter.py` (and `config/backend_registry.json` if needed).
3. Keep CLI args consistent via `cli_adapter` helpers (log-json, log-sandbox, preflight, qa-policy).
4. Document new flows in `docs/` and add a smoke test (`scripts/smoke_audio_pipeline.sh`, `scripts/smoke_rank_inject.sh`).
5. For Automator/GUI changes, prefer env/config indirection (`config/automator.env`, `PIPELINE_DRIVER`, `--mode full`) over hard-coded paths.
6. Validate outputs with `tools/validate_io.py` and schemas; update `docs/COMMANDS.md` and `docs/DEBUGGING.md` with new flags/behaviors.
7. Guardrails: keep `scripts/check_sidecar_deps.sh` executable; enforce allowed binaries for sidecar; preserve `pipeline_version`/fingerprints.

---

## Data/processing guarantees (SLO-style)

- **Schema stability:** `.features.json` and `.merged.json` are stable; compatibility copies retain legacy naming.
- **Provenance:** Config fingerprints include tempo backend, QA thresholds, cache backend, and sidecar status; `pipeline_version` stamped on artifacts.
- **Fallback behavior:** Sidecar order Essentia → Madmom → librosa; warnings recorded; `--require-sidecar` to enforce failure.
- **Output hygiene:** Timestamped primary artifacts to avoid clobber; non-timestamped compatibility copies for downstream consumers.
- **Validation hooks:** `tools/validate_io.py` with `schemas/`; extractor and injectors warn on schema drifts; neighbor writer enforces schema/size caps.
- **Logging hygiene:** Redaction (`LOG_REDACT`, `LOG_REDACT_VALUES`), sandbox scrubbing of beats/neighbors (`LOG_SANDBOX`), optional structured logs (`LOG_JSON`).

---

## Interfaces & integration points

- **Entry points:** `automator.sh` (drag/drop), `tools/pipeline_driver.py` (`--mode hci-only|full`), `ma-extract`, `ma-pipe`, `python3 -m tools.audio_metadata_probe`, injectors/ranker CLIs.
- **Config surfaces:** `ma_config/pipeline.py`, `ma_config/audio.py`, `config/*.json` (backend registry, cache, logging, tempo confidence), env overrides (`HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS`, `CACHE_BACKEND`, `LOG_*`, `QA_POLICY`).
- **Artifacts:** Features/sidecar/merged/pack/client/HCI/neighbors/run_summary/engine_audit.
- **Tests/guardrails:** Import smoke tests, naming contract tests (`tests/test_pipeline_driver_outputs.py`), config override tests, sidecar preflight executable test.
