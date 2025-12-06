# Lyric Intelligence Engine — Dev Host (Phase 1–3)

Deterministic, Billboard-aligned lyric pipeline for the Host. No generation, no hit scoring.

## Canonical schema (SQLite)

- `songs(song_id, title, artist, year, peak_position, weeks_on_chart, source)`
- `lyrics(lyrics_id, song_id, raw_text, clean_text, source)`
- `sections(section_id, lyrics_id, label, start_line, end_line)`
- `lines(line_id, lyrics_id, section_label, line_number, text, word_count, syllable_count, rhyme_key, internal_rhyme_flag)`
- `features_line` with sentiment/POV/explicit/sonic-texture/theme/concreteness per line
- `features_song` with structural stats, lexical diversity, repetition/hook density, POV ratios, rhyme density, concreteness, theme bins, tempo/duration scaffolding
- `features_song_vector` dense numeric array for lane prep

## Phase 1 — Normalize corpora

```bash
python3 tools/lyric_intel_engine.py phase1-normalize \
  --billboard-spine data/external/weekly/rwd_billboard_hot100.csv \
  --kaggle-year-end data/external/year_end/year_end_hot_100_lyrics_kaylin_1965_2015.csv \
  --hot100-lyrics-audio data/external/lyrics/hot_100_lyrics_audio_2000_2023.csv \
  --fallback-top100 data/external/year_end/year_end_hot_100_lyrics_kevin_1950_2015/merged_top100.csv \
  --core-csv data/core_1600_with_spotify_patched.csv \
  --db data/lyric_intel/lyric_intel.db --reset
```

- Priority: UT Austin billboard spine → Kaggle year-end (primary lyrics) → Hot100 lyrics+audio (primary lyrics) → Top100 fallback (gap fill).
- Coverage report targets Core1600 (goal ≥0.95).
- Stores raw lyrics in DB only; no raw lyrics in CLI output.

## Phase 2/3 — Feature extraction

```bash
python3 tools/lyric_intel_engine.py phase2-features \
  --db data/lyric_intel/lyric_intel.db \
  --concreteness-lexicon /path/to/brysbaert_concreteness.csv
```

- Baseline: sectionization (bracket tags → INTRO/VERSE/PRE/CHORUS/POST/BRIDGE/OUTRO), line metrics, lexical diversity, repetition/hook density, sentiment (VADER if available), POV ratios, explicitness.
- Advanced: rhyme density (end + internal), sonic texture (alliteration/assonance/consonance heuristics), theme bins (love/heartbreak/empowerment/nostalgia/flex/spiritual/family/small-town), concreteness (Brysbaert CSV optional), prosody scaffolding (syllable density using duration/tempo when present).
- Dense numeric vector written to `features_song_vector` for lane discovery.

## Data safety & guardrails

- No lyric generation, no hit prediction.
- Billboard-centric identity (song_id slug by title/artist/year hash); dedupe prefers UT Austin spine then primary corpora.
- Raw lyrics never emitted to logs/CLI; only stored in SQLite. Features/coverage outputs are numeric counts.
- Re-run `--reset` to rebuild without touching upstream raw files.

## STT sidecar wrapper (WIP ingest)

Use the wrapper to avoid shell history expansion on paths with `!` and to keep caches local:

```bash
scripts/run_lyric_stt_sidecar.sh \
  --audio '/path/To/File with ! chars.wav' \
  --song-id my_song_id \
  --title "My Song" --artist "Me" --year 2025 \
  --db data/lyric_intel/lyric_intel.db \
  --out features_output/lyrics/my_song_id.lyric_intel.json \
  --no-vocal-separation \
  --transcript-file /path/to/transcript.txt
```

- Wrapper disables shell history expansion for the session and sets local caches (`XDG_CACHE_HOME`, `WHISPER_CACHE_DIR`).
- Prefer single quotes around paths containing `!` when calling directly from zsh.

## Lyric Confidence Index (LCI)

- LCI is a lyric-only, deterministic index built from `features_song` (no raw lyrics).
- Axes (default v1): `structure_fit`, `prosody_ttc_fit`, `rhyme_texture_fit`, `diction_style_fit`, `pov_fit`, `theme_fit` — weighted via calibration JSON (default honors `LYRIC_LCI_CALIBRATION` or `calibration/lci_calibration_us_pop_v1.json`).
- Calibration JSON carries component weights, axis z-score parameters, aggregation targets, and `calibration_profile`.
- Stored in `features_song_lci`; exported as `lyric_confidence_index` with axes + score + calibration_profile in the bridge payload.
- Lanes: songs carry `tier` (chart-based) + `era_bucket`; lane norms (LCI/TTC means/std) can be built via `tools/lyric_lci_norms.py`. When norms are available, overlay z-scores vs the lane are emitted under `lyric_confidence_index.overlay`.

## Time-To-Chorus (TTC) heuristic v1

- Stored in `features_ttc` (seconds to first chorus, bars to chorus if tempo known, estimation_method, profile).
- Heuristic: find first chorus label; if duration is known, split evenly across sections; otherwise fallback seconds/section. Convert to bars when tempo is available.
- Exported in bridge payload as `ttc_profile`.

## Bridge payload (lyric)

Each exported song contains:

```json
{
  "song_id": "...",
  "title": "...",
  "artist": "...",
  "year": 2024,
  "lyric_intel": { "structure_profile": ..., "style_profile": ..., "sentiment_profile": ..., "rhyme_profile": ..., "theme_profile": ..., "prosody_profile": ..., "vector": [...] },
  "lyric_confidence_index": {
    "axes": {...}, "raw": 0.7, "score": 0.72, "calibration_profile": "lci_us_pop_v1",
    "lane": {"tier": 1, "era_bucket": "2015_2024", "profile": "lci_us_pop_v1"},
    "overlay": {"axes_z": {...}, "lci_score_z": 0.2, "ttc_seconds_z": -0.1}
  },
  "ttc_profile": { "ttc_seconds_first_chorus": 24.0, "ttc_bar_position_first_chorus": null, "estimation_method": "ttc_rule_based_v1", "profile": "stub" }
}
```

Raw lyrics are never emitted; only features and indices are exposed.
