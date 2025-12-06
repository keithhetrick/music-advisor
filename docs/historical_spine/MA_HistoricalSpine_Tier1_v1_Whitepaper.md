# Music Advisor Historical Spine — Tier 1 v1 Whitepaper

**Version:** 1.0 (Tier 1 v1 — Frozen Baseline)  
**Date:** 2024-11-23  
**Maintainer:** Keith Hetrick / Music Advisor AudioTools

---

## 1. Purpose & Scope

This document defines **Tier 1 of the Music Advisor Historical Spine (v1)** and freezes its behavior and data assumptions for versioning.

Tier 1 v1 is the **strongest historical echo band** used by Music Advisor’s audio logic:

- It encodes a curated set of **Billboard Year-End Hot 100 Top 40 songs** across 40 years.
- It provides **audio features + lanes** for use in **HCI_v1**, similarity / echo calculations, and other analysis.
- It is **read-only** from the perspective of downstream systems: this whitepaper documents the canonical behavior and constraints.

Out of scope for this document:

- Tier 2 / Tier 3 design (e.g., full Year-End Top 100 or 200).
- HCI_v1 math and calibration details.
- Local WIP feature extraction pipeline (handled elsewhere).

---

## 2. Tier 1 v1 Definition

### 2.1 Conceptual Definition

**Tier 1 Historical Spine v1**:

- **Universe:** Billboard **Year-End Hot 100** chart.
- **Selection rule:** **Top 40** tracks per Year-End chart.
- **Years covered:** **1985–2024** inclusive.
- **Cardinality:** 40 years × 40 ranks = **1600 tracks** (canonical set).

This tier is intended to:

- Capture a **dense, high-signal echo** of successful songs.
- Provide a **historically grounded reference cohort** for evaluating modern WIP audio.

### 2.2 Concrete Artifacts (Files & Tables)

Core CSVs in the repo:

- `data/spine/spine_core_tracks_v1.csv`  
  Canonical track list (1600 rows) with chart metadata:

  - `spine_track_id` (string key; unique per Tier 1 track)
  - `year` (Billboard Year-End year)
  - `chart` (e.g., `HOT_100`)
  - `year_end_rank` (1–40)
  - `artist`, `title`
  - `echo_tier` (for Tier 1: `EchoTier_1_YearEnd_Top40`)
  - `spotify_id` and join metadata where available.

- `data/spine/spine_master_v1.csv`  
  Master Tier 1: core metadata + merged audio features.

- `data/spine/spine_master_v1_lanes.csv`  
  Lane-ified Tier 1: master + derived columns:
  - `tempo_band`
  - `valence_band`
  - other banded/clustered fields
  - `has_audio` flag.

SQLite database:

- `data/historical_echo/historical_echo.db`  
  Key Tier 1 table:
  - `spine_master_v1_lanes` — Tier 1 lanes imported from CSV.

---

## 3. Data Sources & External Datasets

Tier 1 v1 favors **static, academically / community-vetted datasets** with precomputed audio features and/or lyrics. No live Spotify API calls are used.

### 3.1 Audio Feature & Lyrics+Audio Datasets

1. **Spotify Dataset 1921–2020, 600k+ Tracks**

   - Creator: **Yamac Eren Ay**.
   - Kaggle: “Spotify Dataset 1921-2020, 600k+ Tracks.”
   - Content: Audio features for 600k+ tracks and artist popularity metrics.
   - Usage: Forms the **base audio source** for `spine_audio_spotify_v1.csv`.

2. **Billboard Year-End Top 100 Features (1970–2020)**

   - Creator: **Tony Rwen**.
   - Kaggle: “billboard-year-end-top-100-features-19702020.”
   - Content: Billboard Year-End Top 100 songs (1970–2020) with Spotify audio features.
   - Usage: Integrated via `data/spine/backfill/spine_audio_from_tonyrwen_v1.csv`.

3. **Billboard Year-End Top Songs (1960–2020)**

   - Creator: **Patrick Chao**.
   - GitHub: `Patrick5225/Billboard-Year-End-Top-Songs`.
   - Content: Every song on Billboard Year-End Hot 100 (1960–2020) with scraped metadata and Spotify-derived audio features.
   - Usage: Integrated via `data/spine/backfill/spine_audio_from_patrick_v1.csv`.

4. **Billboard Hot-100 [2000–2023] Data with Features**

   - Creator (Kaggle handle): **suparnabiswas (Rune)**.
   - Kaggle: “billboard-hot-1002000-2023-data-with-features.”
   - Content: Combines Billboard Hot-100, Genius lyrics, and Spotify audio features for 2000–2023.
   - Usage in repo:
     - `data/external/lyrics/hot_100_lyrics_audio_2000_2023.csv`
     - Backfill: `data/spine/backfill/spine_audio_from_hot100_lyrics_audio_v1.csv`.

5. **50 Years of Pop Music Lyrics (1965–2015)**

   - Creator: **Kaylin Pavlik**.
   - GitHub: `walkerkq/musiclyrics`.
   - Content: Lyrics for Billboard Year-End Hot 100 songs, used for lyrics and future lyric-intelligence work.

6. **Additional static audio sources used for Tier 2 (credit only; Tier 1 v1 unchanged)**

   These datasets were added to improve Tier 2 (Year-End Top 100) coverage and are listed here for attribution. Tier 1 v1 artifacts remain unchanged.

   - **Spotify Audio Features for Billboard Hot 100**

     - Creator: **elpsyk** (Kaggle).
     - Repo path: `data/external/weekly/Spotify Audio Features for Billboard Hot 100 - elpsyk/billboard_top_100_final.csv`
     - Content: Billboard Top 100 with Spotify audio features; used for Tier 2 backfill.

   - **600 Billboard Hot 100 Tracks (with Spotify Data)**
     - Creator: **The Bumpkin** (Kaggle).
     - Repo path: `data/external/weekly/600 Billboard Hot 100 Tracks (with Spotify Data) - The Bumpkin.csv`
     - Content: 600 Hot 100 tracks with Spotify-derived audio features; used for Tier 2 backfill.

### 3.2 Chart Backbone (Contextual, Not Tier 1 Audio)

Additional chart-only sources that inform the **historical spine design** (Tier 1/2/3 planning) but are not directly used as Tier 1 audio inputs:

1. **UT Austin — rwd-billboard-data**

   - Maintainer: **UT Data / Christian McDonald**.
   - GitHub: `utdata/rwd-billboard-data`.
   - Content: Long-running weekly archives of **Billboard Hot 100** and **Billboard 200** (back to 1958 and 1967 respectively).
   - Usage: Weekly backbone and cross-validation for chart histories and potential future tiers.

2. **Billboard Year-End Hot 100 Singles USA**
   - Creator: **liquidgenius1** (Kaggle).
   - Kaggle: “billboard-yearend-hot-100-singles-usa.”
   - Content: Compiled Year-End Hot 100 charts across many years.
   - Usage: Additional Year-End cross-check & historical reference.

These chart sources are used for **cross-validation, expansion design**, and future Tier 2/3 cohorts, not as direct audio-feature sources in Tier 1 v1.

---

## 4. Data Model & Semantics

### 4.1 Key Fields

For each Tier 1 track in `spine_master_v1.csv` / `spine_master_v1_lanes.csv` / `spine_master_v1_lanes` (DB):

- `spine_track_id` — canonical primary key.
- `year` — Billboard **Year-End year**, 1985–2024.
- `chart` — `HOT_100`.
- `year_end_rank` — integer 1–40.
- `artist`, `title` — as standardized in `spine_core_tracks_v1.csv`.
- `echo_tier` — `EchoTier_1_YearEnd_Top40` for all Tier 1 rows.

Audio feature columns (when available), aligned across all sources:

- `tempo`
- `loudness`
- `danceability`
- `energy`
- `valence`
- `acousticness`
- `instrumentalness`
- `liveness`
- `speechiness`
- `duration_ms`
- `key`
- `mode`
- `time_signature`

Derived lane columns:

- `tempo_band`
- `valence_band`
- Other banded / bucketed representations used for echo lane comparisons.

Presence flag:

- `has_audio`:
  - `1` if **core audio fields are present and parseable** (e.g., `tempo`, `loudness`, `valence`).
  - `0` otherwise.

### 4.2 Semantics of `has_audio`

`has_audio` is the **only trustworthy indicator** that a Tier 1 row has usable audio features:

- All audio-based statistics, distributions, or comparisons must **filter to `has_audio = 1`**.
- Lane columns are only meaningful when `has_audio = 1`; they may be blank or sentinel for `has_audio = 0`.

---

## 5. Construction Pipeline (Tier 1 v1)

This section describes **how Tier 1 v1 is built**, not how it must be used downstream.

### 5.1 High-Level Steps

1. **Core spine assembly**

   - Build `data/spine/spine_core_tracks_v1.csv` from Year-End Hot 100 Top 40 lists (1985–2024).
   - This defines the 1600 canonical rows.

2. **Base audio join (Yamaerenay)**

   - Join `spine_core_tracks_v1.csv` to Yamaerenay’s Spotify dataset on:
     - normalized `artist`
     - normalized `title`
     - approximate `year`.
   - Result: `data/spine/spine_audio_spotify_v1.csv` (base coverage).

3. **Backfills (Tonyrwen, Patrick, Hot 100 lyrics+audio)**  
   Each backfill script:

   - Loads `spine_core_tracks_v1.csv`.
   - Builds an index on `(year, normalized artist, normalized title) → spine_track_id`.
   - Streams the external dataset, normalizes fields, and aligns to `spine_track_id`.
   - Emits a `spine_audio_from_<source>_v1.csv` file with the common audio schema.

   Backfills:

   - `data/spine/backfill/spine_audio_from_tonyrwen_v1.csv`
   - `data/spine/backfill/spine_audio_from_patrick_v1.csv`
   - `data/spine/backfill/spine_audio_from_hot100_lyrics_audio_v1.csv`

4. **Audio enrichment / merge**

   Script: `tools/spine/spine_backfill_audio_v1.py`:

   - Input:
     - `data/spine/spine_audio_spotify_v1.csv` (base)
     - One or more `--extra-audio` backfill CSVs.
   - Output:
     - `data/spine/spine_audio_spotify_v1_enriched.csv`.

   Behavior:

   - Start from base audio.
   - For each extra source, fill missing audio fields for matching `spine_track_id`s.
   - Priority is conservative: **never overwrite** good existing values unless explicitly configured.

5. **Master + lanes**

   - `tools/spine/build_spine_master_v1.py`

     - Merges `spine_core_tracks_v1.csv` + `spine_audio_spotify_v1_enriched.csv`.
     - Ensures the **core `year` column is canonical** and preserved; audio-dataset `year` fields are renamed/dropped to avoid collisions.
     - Output: `data/spine/spine_master_v1.csv` (1600 rows).

   - `tools/spine/build_spine_master_lanes_v1.py`
     - Consumes `spine_master_v1.csv`.
     - Computes `has_audio` and derived lane fields.
     - Output: `data/spine/spine_master_v1_lanes.csv`.

6. **DB import**

   - `tools/spine/import_spine_master_lanes_into_db_v1.py`
     - Imports `spine_master_v1_lanes.csv` into:
       - `data/historical_echo/historical_echo.db`
       - table `spine_master_v1_lanes` (dropping/recreating the table when `--reset` is used).

### 5.2 Typical Rebuild Commands

From repo root:

```bash
cd ~/music-advisor
source .venv/bin/activate

# Rebuild enriched audio
python tools/spine/spine_backfill_audio_v1.py \
  --extra-audio data/spine/backfill/spine_audio_from_tonyrwen_v1.csv \
  --extra-audio data/spine/backfill/spine_audio_from_patrick_v1.csv \
  --extra-audio data/spine/backfill/spine_audio_from_hot100_lyrics_audio_v1.csv

# Rebuild master + lanes
python tools/spine/build_spine_master_v1.py \
  --core  data/spine/spine_core_tracks_v1.csv \
  --audio data/spine/spine_audio_spotify_v1_enriched.csv \
  --out   data/spine/spine_master_v1.csv

python tools/spine/build_spine_master_lanes_v1.py \
  --master data/spine/spine_master_v1.csv \
  --out    data/spine/spine_master_v1_lanes.csv

# Import into DB
python tools/spine/import_spine_master_lanes_into_db_v1.py \
  --db          data/historical_echo/historical_echo.db \
  --spine-lanes data/spine/spine_master_v1_lanes.csv \
  --reset
```

---

## 6. Coverage & Quality (Frozen v1 Metrics)

After the latest backfills and rebuild (Tier 1 v1):

- **Total Tier 1 rows:** 1600
- **Rows with audio (`has_audio = 1`):** 1340
- **Rows without audio (`has_audio = 0`):** 260

### 6.1 Per-Year Coverage (High-Level Summary)

- For **1985–2020**, most years have **33–39 tracks with audio** out of 40.
- For **2021–2024**, coverage is sparse:
  - 2021: 9 / 40 with audio
  - 2022: 0 / 40 with audio
  - 2023: 0 / 40 with audio
  - 2024: 1 / 40 with audio

Interpretation:

- Tier 1 v1 is **audio-dense and highly usable for 1985–2020**.
- 2021–2024 entries are **present for metadata / lyrics / ranking** but **mostly lack audio features** in v1, due to:
  - Limited overlap with pre-2024 static audio datasets.
  - No use of live Spotify audio features API (deprecated / restricted for new apps).

### 6.2 Usage Rules

- For any **audio-based operation** (HCI_v1, similarity, lane statistics, etc.):

  - Always filter to `has_audio = 1`.
  - Optionally, restrict to `year BETWEEN 1985 AND 2020` for the densest echo.

- For **metadata / lyrics / chart context**, all 1600 rows are valid, independent of `has_audio`.

---

## 7. Design Constraints & Decisions

Key constraints behind Tier 1 v1:

1. **Static datasets only; no live Spotify audio features API**

   - As of late 2024, Spotify’s Audio Features / Audio Analysis endpoints are deprecated or restricted for new apps; Tier 1 v1 is designed to rely solely on **offline, static datasets** collected before deprecation or via third parties.

2. **Conservative matching**

   - Matching logic prefers **high-precision** over maximum coverage.
   - Tracks without confident `(year, artist, title)` matches to any audio dataset remain with `has_audio = 0`.

3. **Single “truth brick” database**

   - `historical_echo.db` is treated as the **master store** for Tier 1 lanes (and related lyric tables), to keep downstream queries simple and reproducible.

4. **No synthetic or guessed audio data**
   - Tier 1 v1 does **not** interpolate, hallucinate, or heuristically invent audio features.
   - If no static feature record is available and no local analysis has been run, the track simply has `has_audio = 0`.

---

## 8. Versioning & Future Directions

### 8.1 Tier 1 v1 (This Document)

This whitepaper defines:

- The **exact cohort** (1600 Year-End Top 40 tracks, 1985–2024).
- The **data model and semantics** (`spine_track_id`, `year`, `has_audio`, lanes).
- The **static data sources** used for audio and lyrics.
- The **coverage state** (1340/1600 with audio) and per-year pattern.
- The **constraints** (no Spotify API, conservative matching).

Tier 1 v1 should be treated as a **frozen baseline** for:

- HCI_v1 calibration.
- Early versions of the Audio Intelligence Engine.
- Comparisons against future Tier 1 revisions (v2, v3…).

### 8.2 Potential Tier 1 v2+ Enhancements (Not Implemented Yet)

Future versions **may** include:

1. **Manual / local overrides layer**

   - File: `data/overrides/spine_audio_overrides_v1.csv`.
   - Generated by running a **local audio feature extractor** (e.g., librosa/Essentia) on missing tracks and writing features under `spine_track_id`.
   - Applied as the **last** `--extra-audio` source to supersede other values.

2. **Additional static audio datasets**

   - Incorporating new Kaggle or academic datasets that:
     - Include reliable audio features.
     - Can be matched to the 1600-song spine on `(year, artist, title)`.

3. **Improved coverage for 2021–2024 and beyond**
   - Either through new static datasets or local feature extraction, to reduce the remaining 260 `has_audio = 0` cases.

Any such changes should be documented as:

- **Tier 1 v2**, v3, etc., with:
  - New coverage stats.
  - Newly added sources.
  - Clear migration notes from v1.

---

## 9. Summary

Tier 1 v1 is a **stable, Billboard-grounded, audio-dense reference cohort**:

- 1600 Year-End Hot 100 Top 40 tracks (1985–2024).
- 1340 tracks with trusted audio features from static datasets.
- Clean, reproducible pipeline: core spine → enriched audio → lanes → `historical_echo.db`.
- Explicit constraints (no Spotify API, conservative matching) to keep the system **boring, measurable, and testable**.

Downstream components (HCI_v1, Audio Intelligence Engine, Music Advisor core) should treat this document as the **canonical contract** for Tier 1 v1 behavior and assumptions.
