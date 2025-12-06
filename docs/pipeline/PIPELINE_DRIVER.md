# Pipeline Driver (`ma_audio_engine.tools.pipeline_driver`)

Status: ✅ Last verified with 12-file payload (adds tempo_norms sidecar + tempo overlay; Automator sidecar non-timestamped, HCI/TTC timestamped).

Unified runner for Automator and CLI flows that stitches together feature extraction, merging, packing, and optional HCI/client post-processing. This script exists to keep shell wrappers thin and to centralize profile/timeout defaults.

## Overview (which mode to pick)

- **`hci-only` (default):** Extract + merge + client/HCI/neighbors. Fast local analysis/diagnostics; outputs the legacy 9-file set (no pack/engine audit).
- **`full`:** Everything in `hci-only` plus pack + `engine_audit.json`. Use for GUI/app or when you need a pack and engine audit in one go.
- **`client-only`:** Extract + merge + client helpers (no HCI builder). Use when you only need client payloads without HCI/neighbors.

## Responsibilities

- Drive the canonical extraction chain: features (with tempo/key sidecar) → equilibrium merge → optional pack writing → optional engine audit + HCI/client.rich/neighbors post-processing.
- Normalize configuration via `ma_config.pipeline` defaults with opt-in overrides from env or a small JSON config file.
- Emit compatibility artifacts (`.client.*`, `.hci.json`) when requested so legacy consumers continue to work.

## Modes and outputs

| Mode          | Steps run                                                                   | Expected outputs (under `--out-dir`)                                                       |
| ------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `client-only` | features → merge → pack (no pack file)                                      | `*.features.json`, `*.sidecar.json`, `*.merged.json`, `.client.txt/.json`, optional extras |
| `hci-only`    | features → merge → pack (no pack file) → HCI builder (`ma_hci_builder.sh`)  | Above + `.client.rich.txt`, `.hci.json`, `.neighbors.json`                                 |
| `full`        | features → merge → pack → engine audit (`run_full_pipeline.sh`) → HCI build | Above + pack file (`*.pack.json`), `engine_audit.json`                                     |

Default output root is `features_output/<YYYY>/<MM>/<stem>/` when `--out-dir` is not provided. All filenames are timestamped except compatibility copies (rich/HCI/client). Canonical entrypoint: `python -m ma_audio_engine.tools.pipeline_driver`; `ma-pipe` remains as a shim for compatibility.

**Outputs per mode (naming, current 12-file payload with tempo norms):**

- Timestamped: `<stem>_<ts>.features.json`, `<stem>_<ts>.merged.json`, `<stem>_<ts>.hci.json`, `<stem>_<ts>.ttc.json`, `<stem>_<ts>.pack.json` (full only).
- Compatibility (non-timestamped): `<stem>.sidecar.json`, `<stem>.tempo_norms.json`, `<stem>.client.txt`, `<stem>.client.json`, `<stem>.client.rich.txt`, `<stem>.client.rich.json`, `<stem>.neighbors.json`, `run_summary.json` (builder).
- The `.tempo_norms.json` sidecar is written alongside the rich artifacts and is used to inject the “TEMPO LANE OVERLAY (BPM)” block into `.client.rich.txt` during the post-processing pass. `.key_norms.json` similarly feeds the “KEY LANE OVERLAY (KEY)” block.
- Sidecar taxonomy (doc-only): extraction sidecars / aux extractors (tempo/key runner writing `<stem>.sidecar.json`; lyric STT/TTC also in this bucket) vs. overlay sidecars (tempo_norms/key_norms writing `<stem>.tempo_norms.json` / `<stem>.key_norms.json`; post-processing only). Filenames remain unchanged.

### Quick decision guide

- Need HCI/clients fast? `--mode hci-only --extras`
- Need pack + engine audit for apps? `--mode full --extras`
- Only need client payloads? `--mode client-only`
- Skip HCI during debugging? Add `--skip-hci-builder` (keeps extract/merge/pack)

### What the extra artifacts are (annotated)

- **Pack (`<stem>_<ts>.pack.json`, full mode):** bundle for GUI/app; contains merged audio payload plus helper fields for clients. Shape-stable; do not hand-edit.
- **Engine audit (`engine_audit.json`, full mode):** provenance log (versions, config fingerprints, backends). Use to debug mismatches and confirm what code/config produced the pack.
- **Run summary (`run_summary.json`):** per-run checklist with timestamps, warnings, backend status, and hashes; lives alongside client/HCI artifacts.

### Run timeline (ASCII)

```text
audio
 └─ features.json + sidecar.json
      └─ merged.json
           └─ pack.json (full) + run_summary.json
                └─ engine_audit.json (full)
                     └─ client.rich.txt + hci.json + neighbors.json
```

### Visual checklist (per mode)

- **client-only:** features.json, sidecar.json, merged.json, client txt/json; run_summary.json (if emitted).
- **hci-only:** above + client.rich.txt, hci.json, neighbors.json, run_summary.json.
- **full:** above + pack.json, engine_audit.json; run_summary.json.

### Pack anatomy (truncated)

```json
{
  "source_audio": "/abs/path/song.wav",
  "audio_payload": { ...merged.json contents... },
  "client_helpers": {
    "hci": {...},
    "neighbors": [...],
    "rich_text": "...",
    "qa": {...}
  },
  "meta": {
    "pipeline_version": "1.5.0",
    "config_fingerprint": "sha256:...",
    "generated_at": "2025-12-01T00:00:00Z"
  }
}
```

- `audio_payload` is the normalized `/audio` JSON (same as `merged.json`).
- `client_helpers` mirrors the compatibility artifacts (HCI, neighbors, rich text, QA).
- `meta` records provenance; do not edit packs manually—regenerate via the driver.

For field-by-field reference, inspect the generated pack with `jq` or `python -m json.tool`; keys are shape-stable and mirror the artifacts listed above. JSON Schema: `docs/schemas/pack.schema.json`.

#### Pack field reference (common keys)

- `source_audio` — original file path.
- `audio_payload` — full merged `/audio` payload (normalized schema).
- `client_helpers.hci` — HCI summary block (mirrors `.hci.json`).
- `client_helpers.neighbors` — neighbor list (mirrors `.neighbors.json`).
- `client_helpers.rich_text` — contents of `.client.rich.txt`.
- `client_helpers.qa` — QA/clipping/silence summary.
- `meta.pipeline_version` — driver version used.
- `meta.config_fingerprint` — hash of config/profile/flags.
- `meta.generated_at` — ISO timestamp.

#### Pack field-by-field (detailed)

- `source_audio`: string path to the analyzed file.
- `audio_payload`: entire merged `/audio` payload (includes `features_full`, axes, meta). Same as `<stem>_<ts>.merged.json`.
- `client_helpers`:
  - `client`: optional compatibility copy of `.client.json`.
  - `hci`: block matching `.hci.json` (scores, axes, historical echo summary).
  - `neighbors`: array matching `.neighbors.json`.
  - `rich_text`: string contents of `.client.rich.txt`.
  - `qa`: QA summary (clipping/silence/tempo confidence).
- `meta`:
  - `pipeline_version`: pipeline driver version string.
  - `config_fingerprint`: hash of config/profiles/flags.
  - `generated_at`: ISO timestamp when the pack was written.
  - `warnings`: optional list of warnings propagated from the run summary/audit.

| Field                      | Meaning                                               |
| -------------------------- | ----------------------------------------------------- |
| `source_audio`             | Absolute path to input audio                          |
| `audio_payload`            | Full merged `/audio` payload                          |
| `client_helpers.client`    | Optional copy of `.client.json`                       |
| `client_helpers.hci`       | HCI summary block                                     |
| `client_helpers.neighbors` | Neighbor list (same as `.neighbors.json`)             |
| `client_helpers.rich_text` | Contents of `.client.rich.txt`                        |
| `client_helpers.qa`        | QA/clipping/silence summary                           |
| `meta.pipeline_version`    | Pipeline driver version                               |
| `meta.config_fingerprint`  | Hash of config/profiles/flags                         |
| `meta.generated_at`        | ISO timestamp                                         |
| `meta.warnings`            | Warnings propagated from run summary/audit (optional) |

### Engine audit (truncated)

```json
{
  "engine_version": "1.5.0",
  "config_fingerprint": "sha256:...",
  "sidecar": { "backend": "essentia", "status": "ok" },
  "artifacts": [
    "features.json",
    "sidecar.json",
    "merged.json",
    "pack.json",
    "hci.json",
    "neighbors.json"
  ],
  "warnings": [],
  "generated_at": "2025-12-01T00:00:00Z"
}
```

- Use to confirm what code/config/backends produced the pack/HCI outputs.
- `warnings` highlights degraded paths (fallback sidecar, missing norms, etc.).

#### Engine audit field reference

- `engine_version` — code version of the engine pipeline.
- `config_fingerprint` — hash of config/profiles/flags.
- `sidecar.backend` / `sidecar.status` — which tempo/key backend ran and its health.
- `artifacts` — list of emitted files for the run.
- `warnings` — degraded/fallback notes.
- `generated_at` — ISO timestamp of audit creation.
- `run_id` (if present) — correlation ID for the run.
- `extras` (if present) — optional metadata fields added by wrappers (e.g., app version).

Schema: `docs/schemas/engine_audit.schema.json`.

| Field                | Meaning                                                     |
| -------------------- | ----------------------------------------------------------- |
| `engine_version`     | Engine code version                                         |
| `config_fingerprint` | Hash of config/profiles/flags                               |
| `sidecar.backend`    | Tempo/key backend used (essentia/madmom/librosa)            |
| `sidecar.status`     | Health of the sidecar step (`ok`/`fallback`/`missing`)      |
| `artifacts`          | Files produced (features/sidecar/merged/pack/hci/neighbors) |
| `warnings`           | Degraded/fallback notes                                     |
| `generated_at`       | ISO timestamp of audit creation                             |
| `run_id`             | Optional correlation ID                                     |
| `extras`             | Optional wrapper metadata (e.g., app version)               |

## Data flow (high level) & config cheat sheet

```text
audio file
  └─ ma_audio_features.py (tempo/key via sidecar)  →  <ts>.features.json + <ts>.sidecar.json
       └─ equilibrium_merge.py                      →  <ts>.merged.json
            └─ pack_writer.py                       →  <ts>.pack.json (full only) + client txt/json
                 └─ run_full_pipeline.sh (full)     →  engine_audit.json
                      └─ ma_hci_builder.sh          →  client.rich.txt + hci.json + neighbors.json
```

- **Defaults:** `ma_config/pipeline.py` seeds `HCI_BUILDER_PROFILE_DEFAULT`, `NEIGHBORS_PROFILE_DEFAULT`, `SIDECAR_TIMEOUT_DEFAULT`.
- **JSON config:** `--config path/to/config.json` overrides the above keys.
- **Env:** `HCI_BUILDER_PROFILE`, `NEIGHBORS_PROFILE`, `SIDECAR_TIMEOUT_SECONDS`, `PIPELINE_PY`.
- **CLI:** `--skip-hci-builder`, `--skip-neighbors`, `--extras`, `--log-json`.

### Defaults and overrides (quick table)

| Setting                   | Default (ma_config/pipeline.py) | JSON key                  | Env var                   |
| ------------------------- | ------------------------------- | ------------------------- | ------------------------- |
| HCI builder profile       | `hci_v1_us_pop`                 | `hci_builder_profile`     | `HCI_BUILDER_PROFILE`     |
| Neighbors profile         | `echo_neighbors_us_pop`         | `neighbors_profile`       | `NEIGHBORS_PROFILE`       |
| Sidecar timeout (seconds) | `300`                           | `sidecar_timeout_seconds` | `SIDECAR_TIMEOUT_SECONDS` |
| Python interpreter        | `.venv/bin/python` (if exists)  | —                         | `PIPELINE_PY`             |

## Usage examples

```bash
# HCI-only run with extras (matches Automator default)
python tools/pipeline_driver.py --mode hci-only --extras --audio ~/song.wav

# Full pipeline to engine audit using a custom profile config
python tools/pipeline_driver.py --mode full --audio ~/song.wav --config ~/cfg/pipeline.json

# Client-only artifacts into an explicit folder
python tools/pipeline_driver.py --mode client-only --audio ~/song.wav --out-dir /tmp/output

# Force recompute with sidecar + skip neighbors (faster dev)
python tools/pipeline_driver.py --mode hci-only --audio ~/song.wav --out-dir /tmp/output \
  --skip-neighbors --extras
```

Example `pipeline.json`:

```json
{
  "hci_builder_profile": "hci_v1_us_pop",
  "neighbors_profile": "echo_neighbors_us_pop",
  "sidecar_timeout_seconds": 120
}
```

## Exit behavior and expectations

- Exits `66` when the provided `--audio` path does not exist.
- Returns non-zero on any step failure (features, merge, pack, engine, HCI builder). Partial artifacts remain in `--out-dir` for debugging.
- If `--extras` is set and HCI builder fails, the script attempts to copy `engine_audit.json` into `*.hci.json` when available.
- Validate outputs with `tools/validate_io.py --root <out_dir>` or `--file <artifact>`; schemas live under `schemas/` (see `docs/EXTRACT_PAYLOADS.md`).

## Failure modes & debugging

- Logs: downstream tools log to stderr; Automator runs mirror to `logs/automator_*.log`. For manual runs, inspect console output and artifacts in `--out-dir`.
- Missing artifacts hints:
  - No `<stem>_<ts>.features.json`: feature step failed (check tempo sidecar command/ffmpeg/essentia deps).
  - Features exist but no `<stem>_<ts>.merged.json`: merge step failed (`tools/equilibrium_merge.py`).
  - Merged exists but no pack/client: pack_writer step failed (check anchors/config).
  - Pack exists but no `engine_audit.json` or rich/HCI: engine or HCI builder failed.
- Quick reruns:
  - Force recompute ignoring cache: add `--force`/`--no-cache` flags in the features command (already set by the driver).
  - Skip slow steps to isolate issues: add `--skip-hci-builder` or `--skip-neighbors`.
  - Validate outputs: `python tools/validate_io.py --root <out_dir>` to catch schema/field issues.
- Sidecar issues: ensure `infra/scripts/check_sidecar_deps.sh` passes; verify `<stem>_<ts>.sidecar.json` exists and `tempo_backend_detail` is `essentia|madmom`.
- Interpreter issues: set `PIPELINE_PY` to a known-good venv (`.venv/bin/python`) if auto-detection picks the wrong Python.

## Integration points

- **Automator (`automator.sh`):** calls `pipeline_driver.py` in `hci-only --extras` mode for drag-and-drop flows; relies on env defaults in `config/automator.env`.
- **macOS app/GUI:** call the same driver with `--mode full --extras` (or `--mode hci-only`) to power drag-and-drop apps that need extract → merge → pack → engine audit → HCI/client rich/neighbors in one action.
- **Tests:** `tests/test_pipeline_driver_config.py` ensures JSON config overrides are honored; `tests/test_pipeline_driver_outputs.py` documents expected file naming; import smoke in `tests/test_pipeline_driver_import.py`.
- **Adapters:** Relies on `ma_config.paths.get_repo_root/get_features_output_root` for path resolution and `ma_config.pipeline` for defaults. Sidecar execution uses the configured timeout and command string passed to `ma_audio_features.py`.
- **Schemas:** Feature/sidecar/merged payload fields are described in `docs/EXTRACT_PAYLOADS.md` (and related schemas under `schemas/`). Use these when validating outputs written by this driver.
- **Debugging:** See `docs/DEBUGGING.md` for failure modes, log locations, rerun tips, and validation commands.

## Safe extension tips

- Keep new env/config knobs in `ma_config/pipeline.py` so Automator and CI pick them up uniformly.
- Add new pipeline steps after merge/pack with clear failure semantics; prefer writing to `--out-dir` using timestamped filenames to avoid clobbering.
- Update this document and `docs/COMMANDS.md` when adding new flags or behavior.
