# Smoke Full Chain (local only)

This is the local smoke runner for the MusicAdvisor pipeline. It is not wired to CI.

## How to run

- Canonical runner:

  ```shell
  ./infra/scripts/smoke_full_chain.sh /path/to/audio.wav
  ```

- With generated test tone:

  ```shell
  SMOKE_GEN_AUDIO=1 ./infra/scripts/smoke_full_chain.sh
  ```

- Strict sidecar (require sidecar, longer timeout):

  ```shell
  SMOKE_REQUIRE_SIDECAR=1 SMOKE_SIDECAR_TIMEOUT_SECONDS=120 ./infra/scripts/smoke_full_chain.sh /path/to/audio.wav
  ```

You can also use the shim `./tools/smoke_full_chain.sh ...`, which simply forwards to the canonical script.

## Environment toggles

- `SMOKE_GEN_AUDIO` (default 0): generate a test tone automatically; ignores input path.
- `SMOKE_REQUIRE_SIDECAR` (default 0): when 1, pass `--require-sidecar` to the extractor; failures/timeouts are fatal. When 0, fallback to librosa is allowed.
- `SMOKE_SIDECAR_TIMEOUT_SECONDS` (optional): overrides sidecar timeout for this run (exported to `SIDECAR_TIMEOUT_SECONDS`).
- `SMOKE_SIDECAR_RETRY_ATTEMPTS` (optional): overrides sidecar retry attempts for this run (exported to `SIDECAR_RETRY_ATTEMPTS`).
- `SMOKE_VALIDATE` (default 1): when 1, runs `tools/smoke_validate_outputs.py` at the end; when 0, skips validation.
- `LOG_JSON` (default 0): enable structured JSON logging.
- `LOG_REDACT` (default 1): redact sensitive paths/values in logs unless set to 0.
- `LOG_SANDBOX` (default 0): enable payload scrubbing for sandboxed logs.

## Outputs

Location: `data/features_output/smoke/<timestamp>/<audio_name>/`

Expected artifacts:

- `smoke.features.json` — extractor output (includes qa_status/qa_gate, feature_pipeline_meta).
- `smoke.sidecar.json` — raw sidecar payload if sidecar ran.
- `smoke.merged.json` — normalized merged payload.
- `smoke.client.json` — client helper JSON (runtime_sec present).
- `smoke.client.rich.txt` — client helper text with enrichments.
- `smoke.hci.json` — HCI payload (synthesized if missing).
- `smoke.synth.client.json` — synthetic client stub only when HCI is synthesized.
- `run_summary.json` — summary with versions and timing.
- `smoke_audio*.wav` — generated test audio when SMOKE_GEN_AUDIO=1.

## Reading failures

- Sidecar timeout: expect `sidecar_status=timeout`, `sidecar_warnings` containing `sidecar_timeout`; strict mode will fail.
- Sidecar invalid payload: expect `sidecar_status=invalid` and `sidecar_payload_invalid` warning; fallback used unless strict.
- Validation failures: `tools/smoke_validate_outputs.py` prints `[ERR] ...` lines; check missing files, tempo backend validity, runtime_sec presence, or malformed JSON.
