# tools/ layout

- `tools/cli/`: User-facing entrypoints (e.g., `ma_audio_features.py`) invoked by Automator and shell scripts. Legacy shims live at `tools/*.py` and forward to `tools/cli/` to preserve existing paths.
- `tools/sidecar_adapter.py` and `adapters/`: Bridges between the pipeline and sidecar backends/registries. Use these to add or swap tempo/key backends without touching callers.
- `tools/*.py`: Pipelines, injectors, calibration helpers, ranking scripts. Prefer keeping shared logic in `src/` or `adapters/` and using thin CLIs here.
  - `pipeline_driver.py` and `pack_writer.py` are shims; canonical code lives in `ma_audio_engine.tools.*` (no sys.path hacks).
- `scripts/`: Shell wrappers used by Automator/drag-and-drop flows.
- Config/profile docs: see `docs/config_profiles.md` for env/CLI override patterns across lyric/TTC/HCI/neighbor tools.
- Pipeline driver docs: `docs/pipeline/PIPELINE_DRIVER.md` for modes/outputs/config; debugging tips in `docs/DEBUGGING.md`.
- Chat backend lives in `tools/chat/` (intents/router/overlays), used by the thin host front door.

Guidelines:

- Add new CLIs under `tools/cli/` and provide a shim in `tools/` only if backward compatibility is required.
- Reuse adapters/registries for cache, logging, QA policy, backend selection, and error guards to keep modules loosely coupled.
- Document new flags and behaviors in `docs/COMMANDS.md` and update `docs/architecture/repo_structure.md` when adding new adapters or registries.

## Sidecars & overlays (tempo/key/TTC)

- Install shared deps: `pip install -e src/ma_config -e shared`
- Tempo norms smoke: `PYTHONPATH=. python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`
- Key norms smoke: `PYTHONPATH=. python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key "C major" --out /tmp/demo.key_norms.json --overwrite`
- TTC smoke: `PYTHONPATH=. python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
- Adapter sanity: `PYTHONPATH=. python - <<'PY'\nfrom tools.sidecar_adapter import run_sidecar\npayload, out, warnings = run_sidecar('tone.wav', None, keep_temp=True)\nprint('ok', bool(payload) or warnings)\nPY`

## Chat backend

- README: `tools/chat/README.md`
- Install: `pip install -e tools/chat`
- Smoke: see README for headless snippet using `chat_router.route_message`.
