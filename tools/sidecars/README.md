# Sidecars (tempo/key/TTC)

Headless CLIs to generate norms/overlays and TTC stubs. Designed for isolated, sparse pulls.

## Quick start (headless)

- Install shared deps: `pip install -e src/ma_config -e shared`
- Tempo norms smoke: `PYTHONPATH=. python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`
- Key norms smoke: `PYTHONPATH=. python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key "C major" --out /tmp/demo.key_norms.json --overwrite`
- TTC smoke: `PYTHONPATH=. python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
- Adapter sanity: `PYTHONPATH=. python - <<'PY'\nfrom tools.sidecar_adapter import run_sidecar\npayload, out, warnings = run_sidecar('tone.wav', None, keep_temp=True)\nprint('ok', bool(payload) or warnings)\nPY`

## Dynamic knobs

- Tempo/key env fallbacks: `TEMPO_NORMS_OPTS`, `KEY_NORMS_OPTS` (JSON), timeouts via `TEMPO_NORMS_TIMEOUT`, `KEY_NORMS_TIMEOUT`.
- TTC env: `TTC_OPTS` (JSON), `TTC_TIMEOUT_SECONDS`, optional remote via `TTC_ENGINE_MODE`/`TTC_ENGINE_URL`.
- Sidecar adapter: `MA_TEMPO_SIDECAR_CMD`/`DEFAULT_SIDECAR_CMD`, `MA_SIDECAR_PLUGIN`, `ALLOW_CUSTOM_SIDECAR_CMD`.

## Tests

- No dedicated sidecar test suite; rely on the smokes above and downstream consumers. Use `make -f docs/Makefile.sparse-smoke sparse-smoke-tempo|key|ttc` for quick checks.
