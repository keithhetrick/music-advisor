# Historical Echo Probe (Tier 1 v1)

CLI: `python tools/hci_echo_probe_from_spine_v1.py`

## Inputs

- `--features`: path to a single-track feature JSON (expects Spotify-style audio features: tempo, loudness, danceability, energy, valence, acousticness, instrumentalness, liveness, speechiness, duration_ms, key, mode, time_signature).
- Optional filters:
  - `--top-k`: number of nearest spine tracks to return (default 10).
  - `--year-min` / `--year-max`: restrict candidate years.
  - `--lanes-only`: limit to tracks with lane metadata (if supported by the script).

## Output

- Prints the top matches with similarity scores; no files are written.
- Uses Tier 1 spine metadata (`data/spine/spine_core_tracks_v1.csv`) as the search space.

## Example

````bash
python tools/hci_echo_probe_from_spine_v1.py \
  --features path/to/track.features.json \
  --top-k 10 \
  --year-max 2020
```text
````
