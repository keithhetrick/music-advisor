# Music Advisor — HCI_v1.2 Specification (Echo-First Architecture)

**Status:** Draft  
**Scope:** Audio Intelligence Engine v1.2, Host combining logic, future Lyric Engine compatibility  
**Core Principle:** _"The Top 40 is the Top 40 of 40 years ago."_  
HCI_v1.2 is fundamentally an **EchoScore** — a measure of how deeply a song sits inside proven hit DNA across decades — with a **small, clearly separated ModernScore overlay**.

---

## 1. Roles in the Architecture

### 1.1 Audio Intelligence Engine (current)

Responsibilities:

- Compute **audio_axes** from audio features:
  - `TempoFit` (0–1)
  - `RuntimeFit` (0–1)
  - `LoudnessFit` (0–1)
  - `Energy` (0–1)
  - `Danceability` (0–1)
  - `Valence` (0–1)
- Compute **EchoScore_audio_raw** from `audio_axes`.
- Calibrate to **EchoScore_audio** using a **frozen benchmark corpus** of real hits.
- Compute **ModernScore_audio_raw** from `audio_axes` against a **modern-only reference slice**.
- Calibrate to **ModernScore_audio**.
- Optionally expose **percentiles** for both echo + modern.
- Emit all of the above in a stable JSON schema.

The engine is **standalone** — the Host never recomputes these values.

### 1.2 Lyric Intelligence Engine (future)

Responsibilities (mirrors Audio Engine):

- Compute **lyric_axes** (6D) from lyrics:
  - e.g. Semantic Clarity, Emotional Specificity, Singability, Concept Originality, Narrative Coherence, Cultural Resonance.
- Compute **EchoScore_lyric_raw** and calibrated **EchoScore_lyric** vs a historical lyric benchmark corpus.
- Compute **ModernScore_lyric_raw** and **ModernScore_lyric** vs a modern lyric slice.
- Optionally expose percentiles.
- Emit all of the above via the same style of JSON schema.

### 1.3 Music Advisor Host (client / UI Layer)

Responsibilities:

- **Ingest** the outputs of the Audio and Lyric engines.
- **Combine** them into a final **HCI_final** and **tier**.
- **Explain** results in plain language:
  - Where the song sits historically.
  - How modern it feels.
  - Why it got that score.
- **Never** refit calibrations or try to “learn” directly from user audio/lyrics.

The Host is intentionally “dumb” logic-wise: its job is orchestration, interpretation, and UX.

---

## 2. Audio Engine: Detailed HCI_v1.2 Flow

### 2.1 Axes Computation

Input: merged feature JSON from the audio feature extractor.  
Output: `audio_axes` in `.hci.json`:

```jsonc
"audio_axes": {
  "TempoFit": 0.71,       // how close tempo is to proven hit tempo band
  "RuntimeFit": 0.94,     // how close duration is to proven hit runtime band
  "LoudnessFit": 0.00,    // how close LUFS is to the reference band
  "Energy": 0.35,
  "Danceability": 0.54,
  "Valence": 0.56
}
```

These are **pure audio-space measurements**, not yet “hit scores.”

### 2.2 EchoScore_audio (HCI_v1 core)

1. **EchoScore_audio_raw**

   A deterministic function of `audio_axes`:

```text
EchoScore_audio_raw = f(TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence)
```

- Implemented currently in `tools/hci_axes.py`.
- Weighted sum / nonlinear transform of axes.
- Output is unbounded in principle (practically ~0–1.2 before calibration).

2. **Calibration corpus (frozen)**

   - Lives under `features_output/YYYY/MM/DD/` for a curated benchmark of **real hits only**.
   - Example: `features_output/2025/11/17` as `pop_us_2025Q4_benchmark_v1`.
   - Contains 100+ songs spanning decades, all with **solid commercial validation** (streams, chart positions, cultural impact).
   - Saved into `data/historical_echo_corpus_2025Q4.csv`.

3. **Calibration fit**

   - Script: `tools/hci_calibration.py fit`
   - Inputs: all `.hci.json` from the benchmark corpus.
   - Computes:

   ```text
   raw_mean_audio
   raw_std_audio
   target_mean = 0.70
   target_std  = 0.18
   ```

- Writes to `calibration/hci_calibration_us_pop_v1.json`.

4. **Calibrated EchoScore_audio**

- Script: `tools/hci_calibration.py apply`
- Uses `zscore_linear_v1`:

```text
z      = (EchoScore_audio_raw - raw_mean_audio) / raw_std_audio
score  = target_mean + z * target_std
EchoScore_audio = clamp_to_0_1( logistic / soft_clip(score) )
```

- Stored as:

```jsonc
"HCI_v1_score_raw": 0.47,
"HCI_v1_score": 0.88
```

- Conceptually, `HCI_v1_score` = **EchoScore_audio**.

5. **Echo percentiles**

   From `historical_echo_corpus_2025Q4.csv`, we can derive:

   ```jsonc
   "echo_percentiles": {
     "all": 0.93,        // top 7% of all benchmark hits
     "modern_2010s+": 0.90,
     "modern_2020s+": 0.87
   }
   ```

### 2.3 ModernScore_audio (overlay)

A second scoring layer to capture **alignment with current sonic norms**:

- Trained or calibrated **only on a modern slice** of the corpus (e.g. 2015+ or 2020+).
- Uses the same `audio_axes`, but:
  - Different `raw_mean_modern`, `raw_std_modern`.
  - Possibly different target mean/std (e.g. 0.6/0.18).
- Output fields (proposed):

  ```jsonc

  "modern_score_raw": 0.52,
  "modern_score": 0.80,
  "modern_percentiles": {
    "modern_2020s+": 0.91
  }
  ```

The **Audio Engine** owns this logic; Host just reads these values.

---

## 3. Lyric Engine: Parallel Design (Future)

The Lyric Intelligence Engine will mirror this pattern:

- `lyric_axes` (6D; separate spec)
- `EchoScore_lyric_raw`, `EchoScore_lyric`
- `ModernScore_lyric_raw`, `ModernScore_lyric`
- Percentiles for echo + modern
- Its own calibration JSON (e.g. `calibration/hci_lyric_us_pop_v1.json`)
- Its own historical echo corpus CSV (e.g. `data/historical_echo_corpus_lyrics_2025Q4.csv`)

No coupling: the audio and lyric calibrations are independent.

---

## 4. Host Combination: Final HCI and Tiers

### 4.1 Per-modality combined scores

The Host computes:

```text

HCI_audio = w_echo_audio   * EchoScore_audio
          + w_modern_audio * ModernScore_audio

HCI_lyric = w_echo_lyric   * EchoScore_lyric
          + w_modern_lyric * ModernScore_lyric

```

With the **design constraint**:

- `w_echo_audio   ≥ 0.7`
- `w_echo_lyric   ≥ 0.7`

Example default:

```text

w_echo_audio   = 0.75
w_modern_audio = 0.25

w_echo_lyric   = 0.75
w_modern_lyric = 0.25

```

### 4.2 Final HCI

```text

W_audio = 0.6
W_lyric = 0.4

HCI_final = W_audio * HCI_audio
          + W_lyric * HCI_lyric

```

If lyrics are missing, the Host can:

- Fallback to `HCI_final = HCI_audio`, and
- Annotate that the lyric axis is “not evaluated (audio only).”

### 4.3 Guardrails

To preserve the **historical echo North Star** and avoid the “every WIP is 1.0” trap:

1. **S-Tier rarity**

   - `HCI_final ≥ 0.97` only if:
     - `EchoPercentile_audio >= 0.97`, and
     - (when available) `EchoPercentile_lyric >= 0.90`.
   - The benchmark corpus itself should show **only a few** songs in this tier.

2. **Echo floor for high ratings**

   - If `EchoScore_audio < 0.60`, cap `HCI_audio ≤ 0.80`.
   - If lyrics exist and `EchoScore_lyric < 0.60`, cap `HCI_final ≤ 0.85`.
   - ModernScore can _nudge_, but cannot rescue weak echo.

3. **WIP penalty**

   - If the track is flagged `is_wip = true`:
     - Apply a soft penalty, e.g. `HCI_final_reported = HCI_final * 0.95`.
     - Or disallow S-tier until loudness/runtime/mix criteria are at least within certain bands.

4. **No double-calibration**
   - Calibration is **only** performed:
     - in Audio Engine (for audio scores) and
     - in Lyric Engine (for lyric scores).
   - The Host never recalibrates or re-normalizes `EchoScore_*` or `ModernScore_*`.

---

## 5. Historical Echo as the Heart of the System

To stay aligned with the founding philosophy:

> “The Top 40 is the Top 40 of 40 years ago.”

- **EchoScore (audio + lyric)** is the _core metric_.
- **ModernScore** is an overlay: helps you stay current but **never outranks** historical resonance.
- The **historical echo corpus** is explicit and inspectable:
  - CSV: `data/historical_echo_corpus_2025Q4.csv` (audio now, lyrics later).
  - Columns: `slug, year, artist, title, tempo_fit, runtime_fit, loudness_fit, energy, danceability, valence, hci_v1_score, in_calibration_set, in_echo_set, ...`.
  - This makes the entire system **auditable** and **explainable**.

---

## 6. Implementation Notes (Current Repo)

- Audio axes + raw HCI: `tools/hci_axes.py`
- Calibration (fit + apply): `tools/hci_calibration.py`
- Historical echo corpus builder: `tools/build_historical_echo_corpus.py`
- Current corpus example: `data/historical_echo_corpus_2025Q4.csv`
- Automator #1: runs feature extraction (`ma_audio_features.py`) and writes `.features.json`.
- Automator #2 (v1.2 target):
  - Locates the track directory for a given audio file/folder.
  - Reads `.features.json`.
  - Calls `hci_axes.py` + `hci_calibration.py` for audio engine outputs.
  - Writes `.hci.json`.
  - Merges client pack + `.hci.json` into `.client.rich.txt`, embedding `EchoScore_audio` + `ModernScore_audio` and relevant diagnostics.

This spec is written to remain valid when the Lyric Intelligence Engine goes live: you just plug in its parallel outputs and update the Host’s combination weights, without needing to change the Audio Engine internals.

```

```
