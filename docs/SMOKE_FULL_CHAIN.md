# Smoke Full Chain

End-to-end smoke test for the MusicAdvisor HCI/client pipeline. Runs locally; not wired to CI.

## Quick Start

```shell
# Default non-strict run with auto-generated test audio
SMOKE_GEN_AUDIO=1 ./infra/scripts/smoke_full_chain.sh

# Run with an existing audio file
./infra/scripts/smoke_full_chain.sh /path/to/audio.wav

# Strict sidecar mode with longer timeout
SMOKE_GEN_AUDIO=1 SMOKE_REQUIRE_SIDECAR=1 SMOKE_SIDECAR_TIMEOUT_SECONDS=120 ./infra/scripts/smoke_full_chain.sh
```

A shim at `./tools/smoke_full_chain.sh` forwards to the canonical script.

---

## Copy-Paste Examples

### Example 1: Default Non-Strict Run

Run smoke with auto-generated test audio. Falls back to librosa if sidecar is unavailable or times out.

```shell
SMOKE_GEN_AUDIO=1 ./infra/scripts/smoke_full_chain.sh
```

Expected behavior: passes even if external sidecar is unavailable (librosa fallback).

### Example 2: Generated Audio with JSON Logging

Run with structured JSON logs for debugging or log aggregation.

```shell
SMOKE_GEN_AUDIO=1 LOG_JSON=1 ./infra/scripts/smoke_full_chain.sh
```

### Example 3: Strict Sidecar Mode with Extended Timeout

Require sidecar to succeed; fail if sidecar times out or returns invalid data.

```shell
SMOKE_GEN_AUDIO=1 \
  SMOKE_REQUIRE_SIDECAR=1 \
  SMOKE_SIDECAR_TIMEOUT_SECONDS=120 \
  SMOKE_SIDECAR_RETRY_ATTEMPTS=2 \
  ./infra/scripts/smoke_full_chain.sh
```

Expected behavior: fails if sidecar is unavailable, times out, or returns invalid payload.

---

## Environment Variables

### Smoke-Specific Toggles

| Variable                        | Default | Purpose                                                                                 |
| ------------------------------- | ------- | --------------------------------------------------------------------------------------- |
| `SMOKE_GEN_AUDIO`               | `0`     | Generate a 6-second 440 Hz test tone; ignores input path argument.                      |
| `SMOKE_REQUIRE_SIDECAR`         | `0`     | When `1`, pass `--require-sidecar` to extractor; sidecar failures become fatal.         |
| `SMOKE_SIDECAR_TIMEOUT_SECONDS` | (unset) | Override sidecar subprocess timeout (exported to `SIDECAR_TIMEOUT_SECONDS` internally). |
| `SMOKE_SIDECAR_RETRY_ATTEMPTS`  | (unset) | Override sidecar retry attempts (exported to `SIDECAR_RETRY_ATTEMPTS` internally).      |
| `SMOKE_VALIDATE`                | `1`     | When `1`, run `tools/smoke_validate_outputs.py` after pipeline; `0` skips validation.   |

### Logging Controls

| Variable      | Default | Purpose                                                                  |
| ------------- | ------- | ------------------------------------------------------------------------ |
| `LOG_JSON`    | `0`     | Emit structured JSON logs (stage timings, events) instead of plain text. |
| `LOG_REDACT`  | `1`     | Redact sensitive strings (paths, hashes) from logs. Set `0` to disable.  |
| `LOG_SANDBOX` | `0`     | Enable payload scrubbing for sandbox/minimal logging mode.               |

---

## Output Directory

Location pattern:

```bash
data/features_output/smoke/<YYYYMMDD_HHMMSS>/<audio_basename>/
```

### Expected Artifacts

| File                      | Description                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| `smoke.features.json`     | Extractor output; includes `qa_status`, `qa_gate`, `feature_pipeline_meta`, tempo backend fields. |
| `smoke.sidecar.json`      | Raw sidecar payload (present only when sidecar backend runs).                                     |
| `smoke.merged.json`       | Normalized/merged feature payload.                                                                |
| `smoke.client.json`       | Client helper JSON; must contain `features.runtime_sec`.                                          |
| `smoke.client.rich.txt`   | Client helper text with HCI enrichments.                                                          |
| `smoke.hci.json`          | HCI payload; synthesized stub if no HCI exists for the track.                                     |
| `smoke.synth.client.json` | Synthetic client stub (only when HCI is synthesized; never overwrites main client).               |
| `run_summary.json`        | Run summary with git SHA, dependency versions, stage timings.                                     |

When `SMOKE_GEN_AUDIO=1`, a generated test audio file (e.g., `smoke_audio_XXXXXX.wav`) is also created.

---

## Validation

### Automatic Validation

By default (`SMOKE_VALIDATE=1`), the smoke script runs the validator after pipeline completion:

```shell
python tools/smoke_validate_outputs.py --root <OUT_DIR>
```

This checks:

- Required files exist (`smoke.features.json`, `smoke.merged.json`, `smoke.client.json`, `smoke.hci.json`, `smoke.client.rich.txt`).
- `tempo_backend` is valid (`librosa` or `external`); forbidden stub values rejected.
- `tempo_backend_detail` is present and valid.
- `tempo_backend_meta.backend` is present.
- `qa_status` and `qa_gate` are present.
- `features.runtime_sec` is present and numeric.
- Synth client does not overwrite main client.

### Manual Validation

Run the validator standalone after a previous smoke run:

```shell
python tools/smoke_validate_outputs.py --root data/features_output/smoke/<timestamp>/<audio_name>
```

---

## Understanding Failures

### Sidecar Timeout

- Symptoms: `sidecar_status=timeout`, `sidecar_warnings` contains `sidecar_timeout`.
- Non-strict mode: falls back to librosa; pipeline completes.
- Strict mode (`SMOKE_REQUIRE_SIDECAR=1`): pipeline exits non-zero.

### Sidecar Invalid Payload

- Symptoms: `sidecar_status=invalid`, `sidecar_warnings` contains `sidecar_payload_invalid`.
- Non-strict mode: falls back to librosa.
- Strict mode: exits non-zero.

### Validation Failures

- `tools/smoke_validate_outputs.py` prints `[ERR] ...` lines.
- Common issues: missing required files, invalid tempo backend fields, missing `runtime_sec`, malformed JSON.

### Exit Codes

| Code | Meaning                                        |
| ---- | ---------------------------------------------- |
| `0`  | Success (all stages + validation passed).      |
| `1`  | Pipeline or validation failure.                |
| `2`  | Missing required input (audio file not found). |
| `64` | Security: output dir outside allowed root.     |

---

## Local Audit Ergonomics

For repeated local testing, use the audit wrapper script:

```shell
./infra/scripts/smoke_audit_local.sh
```

Or with an audio file:

```shell
./infra/scripts/smoke_audit_local.sh /path/to/audio.wav
```

The wrapper sets sensible defaults (`SMOKE_GEN_AUDIO=1` if no path provided) and prints active toggles before running.

---

## Pipeline Stages

The smoke script runs these stages in order (with `LOG_JSON=1`, each emits `stage_start`/`stage_end` events):

1. `ma_audio_features` — feature extraction (tempo, key, energy, etc.)
2. `equilibrium_merge` — normalize/merge features
3. `pack_writer` — build client helper payloads
4. `synthesize_hci` — synthesize HCI stub if missing (writes `smoke.synth.client.json`)
5. `hci_final_score` — recompute final HCI score
6. `philosophy_hci` — add philosophy annotations to HCI
7. `echo_hci` — add echo annotations to HCI
8. `merge_client_hci` — merge client and HCI into rich text
9. `philosophy_client` — add philosophy to client rich
10. `echo_client` — add echo to client rich
11. `log_summary` — write run summary with versions
12. `smoke_validate_outputs` — validate outputs (if `SMOKE_VALIDATE=1`)

---

## Notes on Schema Fields

### `runtime_sec`

The `features.runtime_sec` field in `smoke.client.json` is populated by `pack_writer.py` from `merged.duration_sec`. This is the canonical source; the smoke script does not backfill it.

### `feature_pipeline_meta`

The `feature_pipeline_meta` object in `smoke.features.json` is populated by `ma_audio_features.py` via `_ensure_feature_pipeline_meta()`. Fields include `source_hash`, `config_fingerprint`, `pipeline_version`, `sidecar_status`, `tempo_backend`, `tempo_backend_detail`, and `qa_gate`.

### `qa_status`

Top-level `qa_status` in `smoke.features.json` is set by the extractor based on QA checks (clipping, silence ratio, low level). Values: `ok`, `warn_clipping`, `warn_silence`, `warn_low_level`, `unknown`.
