# Robustness & Hardening Checklist

This project already runs client-only and passes smoke/automator. Use this checklist to harden further:

## Validation

- Run `python tools/validate_io.py --root features_output/...` after batches to flag malformed features/merged/client artifacts.
- Add schema checks in CI when feasible; treat warnings as soft failures until confident.

## Resilience & retries

- Wrap external helpers (tempo sidecar, optional HCI probes) with bounded retries + timeouts; mark runs as degraded on fallback. Suggested default: 1 retry, 30s timeout.
- Surface retry counts in `run_summary.json`.

## Determinism & provenance

- Record: input audio hash, code version (git SHA if available), calibration version/date, numpy/librosa/essentia versions, and random seeds (if any) into `run_summary.json` and rich headers.
- Emit a “degraded” flag when optional deps (e.g., madmom) are missing.

## Resource controls

- Enforce per-track concurrency limits; prefer a small worker pool over unbounded parallelism.
- Guardrails: warn when downsampling/truncation occurs; cap memory usage for large files where possible.

## QA gates

- Tighten QA policies: silence/clipping thresholds, tempo confidence floors. In strict mode, halt or mark the track failed with explicit reasons.
- Keep a lenient mode for exploratory runs.

## Performance

- Cache sidecar results by audio hash to skip recompute on repeats.
- Add a batch runner that can resume from partial progress using checkpoints.

## Observability

- Structured logging (JSON) per track with a correlation ID; summarize warnings/errors at job end.
- Optional metrics export (counts, durations, retries, failures) if you wire to a dashboard later.

## Testing

- Golden-file tests for: short/long audio, loud/quiet, off-tempo, stereo/mono, malformed headers.
- Fuzz a handful of malformed inputs (zero-length, bad WAV headers) to keep parsers defensive.

## Operations

- Maintain a “known issues & fallbacks” section (e.g., madmom missing, low tempo confidence) in the operator guide.
- Keep calibration/version notes in rich headers (already present) and update when the spine/calibration refreshes.
