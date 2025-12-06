# Lyric WIP Bundle Contract

This contract describes the JSON the lyric subsystem can hand to the Music Advisor client after running the WIP pipeline.

## Shape

```json
{
  "song_id": "...",
  "title": "...",
  "artist": "...",
  "year": 2024,
  "lane": { "tier": "WIP", "era_bucket": "2015_2024" },
  "lci": {
    "score": 0.72,
    "raw": 0.74,
    "calibration_profile": "lci_us_pop_v1",
    "axes": {
      "structure_fit": 0.96,
      "prosody_ttc_fit": 0.95,
      "rhyme_texture_fit": 0.53,
      "diction_style_fit": 0.81,
      "pov_fit": 0.99,
      "theme_fit": 0.17
    },
    "percentiles": {
      "overall": 0.86,
      "structure_fit": 0.8,
      "prosody_ttc_fit": 0.87,
      "rhyme_texture_fit": 0.56,
      "diction_style_fit": 0.07,
      "pov_fit": 0.9,
      "theme_fit": 0.17
    }
  },
  "ttc": {
    "ttc_seconds_first_chorus": null,
    "ttc_bar_position_first_chorus": null,
    "estimation_method": "ttc_rule_based_v1",
    "profile": "ttc_us_pop_v1",
    "ttc_confidence": "low"
  },
  "neighbors": [
    {
      "song_id": "...",
      "title": "...",
      "artist": "...",
      "year": 2003,
      "similarity": 0.99
    }
  ]
}
```

## Responsibilities

- Lyric subsystem (this repo):
  - Runs STT + features + LCI + TTC + neighbors (via WIP pipeline).
- Produces bridge JSON + neighbors JSON; overlay percentiles come from norms (default honors `LYRIC_LCI_NORMS_PATH` or `calibration/lci_norms_us_pop_v1.json`).
  - `ma_lyric_engine.bundle.build_bundle()` can consolidate bridge + neighbors into the bundle shape above.
- Music Advisor client:
  - Calls the pipeline or consumes the bundle.
  - Renders GUI narrative; applies any additional business logic.

## Notes

- Percentiles come from lane norms (tier + era). If norms are missing, percentiles may be absent.
- TTC v1 is lyric-structure-based; `ttc_confidence` is a coarse indicator of reliability (high/medium/low).
- Neighbors use cosine similarity over `features_song_vector`; deduping is a display concern (report dedupes for readability).
- Golden WIP: we keep at least one regression fixture (e.g., “Wake up Grandma. Wake up!”) to track calibration drift.
