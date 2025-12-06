# Spine Backfill Scripts (Tier 1 v1)

How to add/understand backfills that enrich the spine with audio features.

| Script                                                         | Source dataset                                                                            | Year coverage (approx) | Output                                                            |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------- | ----------------------------------------------------------------- |
| `tools/spine/build_spine_audio_from_tonyrwen_v1.py`            | `data/external/year_end/year_end_top_100_features_tonyrwen_1970_2020/primary_dataset.csv` | 1970–2020              | `data/spine/backfill/spine_audio_from_tonyrwen_v1.csv`            |
| `tools/spine/build_spine_audio_from_patrick_v1.py`             | `data/external/year_end/year_end_hot_100_spotify_features_patrick_1960_2020.csv`          | 1960–2020              | `data/spine/backfill/spine_audio_from_patrick_v1.csv`             |
| `tools/spine/build_spine_audio_from_hot100_lyrics_audio_v1.py` | `data/external/lyrics/hot_100_lyrics_audio_2000_2023.csv`                                 | 2000–2023              | `data/spine/backfill/spine_audio_from_hot100_lyrics_audio_v1.csv` |
| `tools/spine/build_spine_audio_from_hot100songs_v1.py`         | `data/external/year_end/year_end_top_100_features_tonyrwen_1970_2020/` + charts           | 1970–2020              | `data/spine/backfill/spine_audio_from_hot100songs_v1.csv`         |
| `tools/spine/build_spine_audio_from_yamaerenay_v1.py`          | `data/external/spotify_dataset_19212020_600k_tracks_yamaerenay/tracks.csv`                | 1900–2021 (probe)      | prints coverage only (stub; no backfill yet)                      |

Merge+apply overrides: `tools/spine/spine_backfill_audio_v1.py` (combines backfills + `data/overrides/spine_audio_overrides_v1.csv`).

## Adding a new backfill (quick guide)

1. Drop the source CSV under `data/external/<name>/`.
2. Inspect headers: `python tools/spine/scan_external_datasets_v1.py` (see `data/DATASET_AUDIO_CANDIDATES.md`).
3. Write `tools/spine/build_spine_audio_from_<name>_v1.py`:
   - Match on `(year, normalized artist, normalized title)` to `spine_core_tracks_v1.csv`.
   - Emit `data/spine/backfill/spine_audio_from_<name>_v1.csv` with available audio feature cols.
4. Add a row to the table above and link the dataset in `data/external/README.md`.
5. Merge via `spine_backfill_audio_v1.py`, then run coverage/missing reports.

## ASCII flow (backfills → merge)

```ascii
[core: spine_core_tracks_v1.csv]
          |
   (backfill scripts)
          v
[data/spine/backfill/*.csv]
          |
[overrides: spine_audio_overrides_v1.csv]
          |
[spine_backfill_audio_v1.py]
          |
[coverage/missing reports]
```
