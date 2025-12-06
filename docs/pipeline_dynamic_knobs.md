# Pipeline & sidecar dynamic knobs

This notes env/CLI hooks for the audio/sidecar pipeline so connection points stay flexible and headless-friendly.

## Sidecar adapter (tempo/key extraction)

- Default command template: `MA_TEMPO_SIDECAR_CMD` (falls back to `DEFAULT_SIDECAR_CMD`, default `python3 tools/tempo_sidecar_runner.py --audio {audio} --out {out}`).
- Plugin runner: `MA_SIDECAR_PLUGIN` (inject custom runner via DI).
- Custom command gate: callers honor `ALLOW_CUSTOM_SIDECAR_CMD` to block non-default templates.
- Safety: respects `security.config.CONFIG.allowed_binary_roots`, resource/time limits, and guarded JSON loading.

## Tempo sidecar runner (Essentia/Madmom/librosa)

- Logging: `LOG_JSON`, `LOG_REDACT`, `LOG_REDACT_VALUES`.
- CLI flags cover inputs/outputs; no extra env toggles required for algorithm selection (prefers Essentia/Madmom if available, else librosa).

## Key/tempo overlays (norms sidecars)

- `tools/tempo_norms_sidecar.py` / `tools/key_norms_sidecar.py` expose behavior via CLI flags (neighbor steps/decay, smoothing, fold bands, etc.). Env fallbacks allowed via `TEMPO_NORMS_OPTS` and `KEY_NORMS_OPTS` JSON (applied only when CLI args are still at defaults); logging via `LOG_JSON`/redaction flags; optional timeouts via `TEMPO_NORMS_TIMEOUT` / `KEY_NORMS_TIMEOUT`.
- Injection into `.client.rich.txt` via `ma_add_tempo_overlay_to_client_rich.py` and `ma_add_key_overlay_to_client_rich.py` is flag-driven; no hidden envs.

## Audio feature extraction

- Uses `ma_audio_engine.adapters` logging/preflight envs (e.g., `LOG_JSON`, redaction flags). See engine knobs in `docs/engine_dynamic_knobs.md`.

## TTC

- TTC sidecar: CLI flags for profile/config/seconds-per-section; env JSON fallback via `TTC_OPTS` (applies only when flags are default); optional timeout via `TTC_TIMEOUT_SECONDS`. Logging via `LOG_JSON`/redaction flags. Remote TTC engine via `TTC_ENGINE_MODE=local|remote` and `TTC_ENGINE_URL` (required when remote).

## Guidance

- Prefer CLI flags for algorithm parameters; use env vars for mode/plugin selection and logging/limits.
- Keep defaults backward compatible; fail fast when required paths/URLs are missing.

## Minimal smoke for targeted pulls

- Tempo norms: `PYTHONPATH=. python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`
- Key norms: `PYTHONPATH=. python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key \"C major\" --out /tmp/demo.key_norms.json --overwrite`
- TTC stub: `PYTHONPATH=. python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
- Sidecar adapter sanity: `PYTHONPATH=. python - <<'PY'\nfrom tools.sidecar_adapter import run_sidecar\npayload, out, warnings = run_sidecar('tone.wav', None, keep_temp=True)\nprint('ok', bool(payload) or warnings)\nPY`
