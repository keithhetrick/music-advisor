# Contributing (Repo Conventions)

## Adding a new audio backfill

- Place the source CSV under `data/external/` (create a descriptive subfolder).
- Add a short entry to `data/external/README.md` (dataset name, path, year span).
- Run `python tools/spine/scan_external_datasets_v1.py` to verify headers/audio cols.
- Implement a script `tools/spine/build_spine_audio_from_<source>_v1.py` following existing backfills:
  - Use `(year, normalized artist, normalized title)` to match `data/spine/spine_core_tracks_v1.csv`.
  - Write output to `data/spine/backfill/spine_audio_from_<source>_v1.csv`.
  - Include only Spotify-style audio feature columns present in the source.
- Add the script to `docs/spine/BACKFILLS.md` (source, coverage, output).
- Merge via `tools/spine/spine_backfill_audio_v1.py` and re-run coverage/missing reports.

## Command docs

- Keep `COMMANDS.md` updated when adding new CLIs or flows.
- Link new design/usage docs from the Reference section in `COMMANDS.md`.

## Payload conventions

- `ma-extract` / `ma-pipe` emit advisory JSON; keep the shape stable (see `docs/pipeline/README_ma_audio_features.md`).
- Prefer UTF-8 CSVs; if adding external data with other encodings, document it.

ASCII flow (new backfill addition):

```ascii
[data/external/<new>.csv]
          |
[scan + inspect headers]
          |
[build_spine_audio_from_<new>_v1.py]
          |
[data/spine/backfill/spine_audio_from_<new>_v1.csv]
```
