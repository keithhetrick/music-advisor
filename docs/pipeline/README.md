# Pipeline quickstart (headless/sparse)

Designed for isolated, sparse pulls and headless use.

## Quick smokes

- Tempo norms: `PYTHONPATH=. python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`
- Key norms: `PYTHONPATH=. python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key "C major" --out /tmp/demo.key_norms.json --overwrite`
- TTC stub: `PYTHONPATH=. python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
- All at once: `make -f docs/Makefile.sparse-smoke sparse-smoke-all`

## Dynamic knobs

- See `docs/pipeline_dynamic_knobs.md` for sidecar adapter/env hooks, overlay env fallbacks, and TTC remote/timeout settings.
- See `docs/engine_dynamic_knobs.md` for engine-specific env switches.

## Notes

- Shared libs install: `pip install -e src/ma_config -e shared` (or `pip install -e .`) to avoid PYTHONPATH tweaks.
- The pipeline driver/pack writer live under `ma_audio_engine.tools.*`; `tools/pipeline_driver.py` is a shim. CLI help: `python -m ma_audio_engine.tools.pipeline_driver --help`.
