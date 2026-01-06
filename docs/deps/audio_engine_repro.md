# Audio Engine Repro (current working stack)

This captures the exact working environment for the audio engine/Automator as of 2026-01-06 so we can recreate it later without guesswork. The current venv comes from an older snapshot; the goal is to make it reproducible and portable.

## Environment (known good)

- Python: 3.11.2 (`/Users/keithhetrick/music-advisor/.venv/bin/python`)
- Core packages: `numpy 1.26.4`, `scipy 1.11.4`, `librosa 0.10.1`, `pydub 0.25.1`, `numba 0.62.1`, `llvmlite 0.45.1`
- Essentia: `2.1-beta6-dev` (built for Python 3.11; imported OK)
- Optional: madmom not installed (Automator warns but proceeds)
- FFmpeg: 8.0.1 on PATH
- macOS: 12 (x86_64)

## Recreate the venv (current state)

> Until we produce a clean Essentia wheel, the easiest path is to reuse/archive the working venv or extract wheels from it.

1. Make a fresh venv (Python 3.11.x):

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

2. Install pinned deps:

   ```bash
   pip install -r requirements.lock
   ```

3. Install Essentia + matching numba/llvmlite (from the working venv snapshot or wheel archive once we create it). Current versions:

   - `essentia==2.1-beta6-dev`
   - `numba==0.62.1`
   - `llvmlite==0.45.1`
   - Wheel cached at `wheels/essentia-2.1b6.dev1110-cp311-cp311-macosx_10_9_x86_64.whl`.
     Example install:

   ```bash
   pip install wheels/essentia-2.1b6.dev1110-cp311-cp311-macosx_10_9_x86_64.whl numba==0.62.1 llvmlite==0.45.1
   ```

4. Verify:

   ```bash
   python - <<'PY'
   import numpy, scipy, librosa, numba, llvmlite, essentia
   print("numpy", numpy.__version__)
   print("scipy", scipy.__version__)
   print("librosa", librosa.__version__)
   print("numba", numba.__version__, "llvmlite", llvmlite.__version__)
   print("essentia", getattr(essentia, "__version__", "unknown"))
   PY
   ./infra/scripts/check_sidecar_deps.sh   # should report essentia ok
   ```

5. Full freeze for this venv: see `docs/deps/audio_engine_freeze.txt`.

## PYTHONPATH for manual tools

When running tools directly (outside Automator), set:

```bash
export PYTHONPATH=.:$PWD/src:$PWD/tools:$PWD/engines/audio_engine/src:$PWD/engines/lyrics_engine/src:$PWD/engines/ttc_engine/src:$PWD/hosts/advisor_host_core/src
```

## Key norms parser fix

We patched key parsing to accept mixed-case accidentals (e.g., `EB major`). Files:

- `tools/key_norms_sidecar.py`
- `tools/key_relationships.py`

## Pending work for full reproducibility

- Produce a Python 3.11 wheel for Essentia (2.1-beta6-dev) and document the build steps/patches; today we rely on the rescued venv.
- Align `pyproject.toml` pins to the working numba/llvmlite combo (0.62.1/0.45.1) and regenerate `requirements.lock`.

## Quick smoke

```bash
source .venv/bin/activate
./infra/scripts/check_sidecar_deps.sh
./automator.sh /path/to/audio.wav
```
