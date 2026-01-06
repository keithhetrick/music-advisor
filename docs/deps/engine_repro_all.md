# Engine Repro (all projects) — snapshot 2026-01-06

Goal: make every engine reproducible on its own and together. This snapshot uses the working venv (Python 3.11.2) and the exact pins/wheels captured in this repo.

## One-shot environment restore

1. New venv (Python 3.11.x):

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

2. Install locked deps + Essentia wheel + matching numba/llvmlite:

   ```bash
   pip install -r requirements.lock
   pip install wheels/essentia-2.1b6.dev1110-cp311-cp311-macosx_10_9_x86_64.whl numba==0.62.1 llvmlite==0.45.1
   ```

3. Optional: install projects editable (if you want editable imports without relying on PYTHONPATH):

   ```bash
   pip install -e engines/audio_engine \
               -e engines/lyrics_engine \
               -e engines/ttc_engine \
               -e engines/recommendation_engine \
               -e hosts/advisor_host_core \
               -e hosts/advisor_host
   ```

4. Verify sidecars (Essentia/tempo) for audio engine:

   ```bash
   ./infra/scripts/check_sidecar_deps.sh
   ```

5. Reference freeze (exact working venv): `docs/deps/audio_engine_freeze.txt`.

## PYTHONPATH (manual runs)

Automator does not need this. For direct tool/sidecar runs:

```bash
export PYTHONPATH=.:$PWD/src:$PWD/tools:$PWD/engines/audio_engine/src:$PWD/engines/lyrics_engine/src:$PWD/engines/ttc_engine/src:$PWD/hosts/advisor_host_core/src
```

## Per-engine quick checks (lightweight)

- Audio engine: `./infra/scripts/check_sidecar_deps.sh` and optionally `python -m ma_audio_engine.tools.pipeline_driver --help`.
- Lyrics engine: `python -m ma_lyrics_engine --help` (or run an existing lyrics test if present).
- TTC engine: `python -m ma_ttc_engine --help`.
- Recommendation engine: `pytest engines/recommendation_engine/tests -q` (or run a smoke CLI if available).
- Host/advisor: `python hosts/advisor_host/cli/ma_host.py --help`.

## Notes

- Essentia wheel is cached locally in `wheels/`. Keep it with the repo for offline installs.
- Pins in `requirements.lock` mirror the current working environment (see freeze for the full list).
- If adding new deps, regenerate `requirements.lock` and update the freeze file.
