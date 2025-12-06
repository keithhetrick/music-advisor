# Extractor Payloads (ma-extract / ma-pipe) — Whitepaper

Authoritative reference for the lightweight advisory JSON emitted by `ma-extract` / `ma-pipe` (and the pipeline driver’s feature step).

## Inputs

- Audio file (`--audio`): wav/aiff/mp3/m4a/flac (local only; no network).
- Output path (`--out`): advisory JSON written to the given file.
- Optional env: `MA_DISABLE_NORMS_ADVISORY=1` to skip norms advisory.

## Output shape (advisory JSON, flat)

- `source_audio`: absolute path to input audio
- `sample_rate`: int
- `duration_sec`: float
- `tempo_bpm`: float
- `key`: string (e.g., "D")
- `mode`: string ("major"/"minor")
- `loudness_LUFS`: float
- `energy`: float [0,1]
- `danceability`: float [0,1]
- `valence`: float [0,1]
- `advisory`: optional block with norms/advice (may be absent if disabled)

## Minimal example payload (annotated)

```json
{
  "source_audio": "/abs/path/song.wav",
  "sample_rate": 44100,
  "duration_sec": 196.2,
  "tempo_bpm": 123.0,
  "key": "D",
  "mode": "minor",
  "loudness_LUFS": -10.5,
  "energy": 0.78,
  "danceability": 0.82,
  "valence": 0.55,
  "advisory": {
    "norms": "optional advisory text or omitted when MA_DISABLE_NORMS_ADVISORY=1"
  }
}
```

- Fields map directly to extractor outputs; no nested shapes here.
- `advisory` is optional; set `MA_DISABLE_NORMS_ADVISORY=1` to omit it and keep the payload lean.
- Use this payload as input to host/chat or recommendation engine when you only need lightweight advisory context.

## Where it flows

- Produced by `ma-extract` / `ma-pipe` / pipeline driver feature step.
- Can be merged into pack/HCI/client artifacts (`merged.json` and downstream outputs).
- Host/chat accepts this as `payload` if you want a lightweight analyze call without running full pipelines locally.
- JSON Schema: `docs/schemas/run_summary.schema.json` (run summary) and advisory payload schema TBA if needed.

### Quick flow (ASCII)

```ascii
audio --> ma-extract / ma-pipe --> advisory JSON (this doc)
                            |
                            +--> merged/pack/HCI/client (pipeline driver)
                            |
                            +--> host/chat payload (POST /chat)
```

## CLI examples

```bash
ma-extract --audio /path/to/song.wav --out advisory.json
MA_DISABLE_NORMS_ADVISORY=1 ma-extract --audio /path/to/song.wav --out advisory.json
ma-pipe --audio /path/to/song.wav --out advisory.json
```

## Validation (schemas)

- Validate single artifact: `python tools/validate_io.py --file path/to/track.features.json`
- Validate entire run folder (features/merged/client/hci): `python tools/validate_io.py --root features_output/YYYY/MM/DD/Track`
- Schemas live in `schemas/`; field references in this doc and `docs/pipeline/README_ma_audio_features.md` for richer nested outputs.

## Notes and invariants

- Schema is consumed by HCI/axes pipelines; keep keys and semantics stable.
- For nested JSON (client-oriented), use the standalone extractor `ma_audio_features.py` (see `docs/pipeline/README_ma_audio_features.md`).
- Tempo/key provenance and confidence live in the sidecar and merged payloads; see `docs/sidecar_tempo_key.md`.
- Sidecar taxonomy (doc-only): extraction sidecars / aux extractors (tempo/key runner, lyric STT, TTC; read audio/primaries) vs. overlay sidecars (tempo_norms/key_norms; post-process features/lanes). Filenames stay as-is.
- Outputs are local-only; no cloud calls. Set `CACHE_BACKEND=noop` if you need read-only runs.

## Flow (advisory extractors)

```text
[local audio file]
       |
   ma-extract / ma-pipe
       v
[advisory JSON (.features.json)]
       |
(optional) downstream HCI/axes/ranking
```
