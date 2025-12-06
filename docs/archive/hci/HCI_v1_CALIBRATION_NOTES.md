# HCI_v1 — Calibration, 0–1 Scale Semantics, and Historical-Echo Alignment

**Status:** v1.1 (US Pop 2025Q4 baseline, frozen)  
**Scope:** Audio-only HCI*v1 for 6-axis structural/emotional analysis  
**Goal:** Explain \_exactly* how HCI*v1 is computed, calibrated, and interpreted – and how a score of `1.0` aligns with the Creative Intelligence Framework (CIF) and the \_Historical Echoes* thesis.

---

## 1. What HCI_v1 Is (and Is Not)

**HCI_v1** is a **continuous, calibrated composite score** derived from a 6-axis description of a track:

1. Tempo_Fit (Gaussian fit to market tempo norms)
2. Runtime_Fit (Gaussian fit to market runtime norms)
3. Energy (0–1, from features_full)
4. Danceability (0–1, from features_full)
5. Valence (0–1, from features_full)
6. Loudness_Fit (Gaussian fit to target LUFS window)

HCI_v1 answers the question:

> “Given a particular market cohort (e.g., US Pop 2025Q4), how strongly does this track sit in the **current sweet-spot** of those six axes?”

Crucially:

- It is **cohort-relative**, not a universal or timeless “goodness” score.
- It is **structural/emotional**, not a direct measure of streams, radio spins, or cultural virality.
- It is one quantitative **layer inside the Creative Intelligence Framework (CIF)** – not the entire intelligence stack.

---

## 2. Axes → Raw HCI_v1 (Uncalibrated)

### 2.1 Input features

We start from `features_full` (as produced by the feature pipeline), which must contain at least:

- `bpm`
- `duration_sec`
- `loudness_lufs`
- `energy` (0–1)
- `danceability` (0–1)
- `valence` (0–1)

### 2.2 Market norms (“baseline”)

Market norms are defined in:

- `calibration/market_norms_us_pop.json`  
  (currently copied from `datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json`)

This JSON provides **MARKET_NORMS**, including:

- `tempo_bpm_mean`, `tempo_bpm_std`
- `runtime_sec_mean`, `runtime_sec_std`
- `loudness_lufs_mean`, `loudness_lufs_std` (or default `-10.5 ± 1.5` if missing)

These parameters define **what “centered” looks like** for the structural axes.

### 2.3 Axis computation

`tools/hci_axes.py` implements:

```python
axes = compute_axes(features_full, market_norms)
```

Conceptually:

- **Tempo_Fit (a0)**  
  `a0 = GaussianFit(bpm | μ = tempo_bpm_mean, σ = tempo_bpm_std)`

- **Runtime_Fit (a1)**  
  `a1 = GaussianFit(duration_sec | μ = runtime_sec_mean, σ = runtime_sec_std)`

- **Energy (a2)**  
  `a2 = clamp(energy, 0.0, 1.0)`

- **Danceability (a3)**  
  `a3 = clamp(danceability, 0.0, 1.0)`

- **Valence (a4)**  
  `a4 = clamp(valence, 0.0, 1.0)`

- **Loudness_Fit (a5)**  
  `a5 = GaussianFit(loudness_lufs | μ = loudness_lufs_mean, σ = loudness_lufs_std)`  
  (defaults to ~`-10.5 ± 1.5` LUFS if not explicitly defined)

Where **GaussianFit** is:

```python
def _gaussian_fit(x, mean, std):
    if x is None or mean is None or std is None or std <= 0:
        return 0.0
    z = (x - mean) / std
    return exp(-0.5 * z * z)  # 1.0 at the mean, falls off as |z| grows
```

The axes are then rounded to 3 decimal places and written out as:

```json
"audio_axes": [a0, a1, a2, a3, a4, a5]
```

### 2.4 Raw HCI_v1 aggregation

Uncalibrated HCI_v1 is simply the **mean of the six axes**:

```python
def compute_hci(axes, cap=None):
    if not axes:
        return 0.0
    h = sum(axes) / len(axes)
    if cap is not None and cap > 0:
        h = min(h, cap)
    return round(h, 3)
```

In practice for v1.1:

- We **do not** pass a `cap` here; the raw HCI value is free to be anything in a plausible numeric range.
- This raw HCI is stored as `HCI_v1_score_raw` in calibrated `.hci.json` files.

---

## 3. Banding for Energy / Dance / Valence

Separately from HCI (which uses continuous axis values), we band emotional axes into `{lo, mid, hi}` using **frozen thresholds** from calibration v1.1:

```python
ENERGY_THRESHOLDS  = (0.360707, 0.373529)
DANCE_THRESHOLDS   = (0.367329, 0.517685)
VALENCE_THRESHOLDS = (0.33, 0.66)
```

Helper:

```python
def _band_from_thresholds(value, (t_lo_mid, t_mid_hi)):
    if value is None: return "unknown"
    v = float(value)
    if v < t_lo_mid:  return "lo"
    if v <= t_mid_hi: return "mid"
    return "hi"
```

And axis-specific wrappers:

- `band_energy(energy)`
- `band_danceability(dance)`
- `band_valence(valence)`

These bands:

- Are derived from the **100-song benchmark calibration** via truth vs ML triage.
- Are **frozen** for v1.1 to keep all layers (benchmark tools, advisor, CIF) aligned.

> **Important:** banding is **for interpretability and truth comparison**, not for HCI computation. HCI uses the continuous values, calibration happens afterward.

---

## 4. Calibration: From Raw HCI to Calibrated 0–1 HCI_v1

### 4.1 Why calibrate?

The raw HCI (mean of six axes) lives in some arbitrary numeric range:

- It depends on the Gaussian shapes for tempo/runtime/loudness.
- It depends on typical energy/dance/valence of the cohort.

To make HCI **interpretable and comparable**, we:

1. Collect **raw HCI values** for a carefully chosen calibration cohort (e.g., `Benchmark_Set_v1_1`, 100 historically meaningful hits).
2. Fit a simple **z-score mapping** so that:
   - The cohort’s mean maps to a chosen **target_mean** (e.g., 0.70).
   - The cohort’s standard deviation maps to **target_std** (e.g., 0.18).

In v1.1, calibration is done with:

```bash
python tools/hci_calibration.py fit \
  --root features_output/2025/11/15/Benchmark_Set_v1_1 \
  --out calibration/hci_calibration_us_pop_v1.json \
  --target-mean 0.70 \
  --target-std 0.18
```

This reads all `.hci.json` files in the benchmark root, extracts their **raw** HCI scores (from the uncalibrated pass), and computes:

- `raw_mean` (μ_raw)
- `raw_std` (σ_raw)

### 4.2 The mapping equation

Calibration uses a straightforward z-score → linear mapping:

Let:

- `h_raw` = uncalibrated HCI (mean of axes) for a track
- `μ_raw` = mean raw HCI of the calibration cohort
- `σ_raw` = std dev of the calibration cohort
- `μ_target` = `target_mean` (e.g., 0.70)
- `σ_target` = `target_std` (e.g., 0.18)

Then:

```text
z           = (h_raw - μ_raw) / σ_raw
h_mapped    = μ_target + z * σ_target
HCI_v1      = clamp(h_mapped, 0.0, 1.0)
```

This is encoded in the `.hci.json` meta as:

```json
"calibration": {
  "scheme":      "zscore_linear_v1",
  "raw_mean":    μ_raw,
  "raw_std":     σ_raw,
  "target_mean": μ_target,
  "target_std":  σ_target
}
```

And at the top level:

- `HCI_v1_score_raw` = `h_raw` (mean of axes, unscaled)
- `HCI_v1_score` = final, clipped, calibrated score in **[0, 1]**

### 4.3 Why 0–1 with clipping?

We explicitly **clip** to [0, 1]:

- Anything below 0 is set to 0.0
- Anything above 1 is set to 1.0

This is deliberate and standard:

- Makes HCI easily composable with other 0–1 scales.
- Keeps scoring intuitive (“0% to 100% sweet-spot fit”).
- Mirrors common ML / analytics practice (min–max scaling with clipping).

---

## 5. What Does a Score of 1.0 Actually Mean?

**Key distinction:**  
`1.0` does **NOT** mean “this is the perfect song” or “there can never be a higher echo.”

Instead, **within this specific cohort and calibration** it means:

> “This track’s raw HCI_v1 is so far into the right tail of the calibration distribution that, when mapped, it exceeds 1.0 and is therefore **saturated at the top of the scale**.”

Mathematically, for v1.1:

- `μ_raw ≈ 0.25983`
- `σ_raw ≈ 0.05592`
- `μ_target = 0.70`
- `σ_target = 0.18`

For example, `2019_dua_lipa__dont_start_now__album` has:

- `HCI_v1_score_raw ≈ 0.392` (mean of axes)
- This is ≈ **2.4 standard deviations above the cohort mean**.
- The z-score mapping pushes it above 1.0; we then clip it back to **1.0**.

So **1.0 really means**:

> “In this six-axis structural/emotional space, and relative to this calibration cohort, this track lives in the **Apex Anchor tier** (≥ ~2–2.5σ above center).”

It is **not** a statement about:

- Timeless perfection
- Moral or artistic value
- Being “better” than iconic tracks from other eras

It is a **statistical statement** about where the track sits in the calibrated 00_core_modern universe.

---

## 6. Qualitative Bands for HCI_v1

To keep HCI_v1 human-readable, we pair the numeric score with qualitative tiers.

A proposed mapping for v1.1:

- **0.90 – 1.00 → Apex Anchor Tier**  
  Modern gravity wells (e.g., `Don't Start Now`, `Flowers`, similar rare apex tracks).  
  These are the songs the system uses as **anchors and reference vectors**.

- **0.75 – 0.89 → Strong Hit Tier**  
  Tracks that are very aligned with the current six-axis sweet-spot and highly competitive in a mainstream context.

- **0.55 – 0.74 → Competitive / On-Trend Tier**  
  Solid, on-trend records; aligned with market norms but not in the extreme tail. These are “healthy” commercial positions for new WIPs.

- **0.35 – 0.54 → Niche / Experimental / Incomplete Tier**  
  May lean deliberately weird, sparse, or outside norms; or may just be early WIP mixes with structural or loudness issues.

- **0.00 – 0.34 → Out-of-Cohort / Edge Tier**  
  Either:
  - Very rough/unfinished audio, or
  - Tracks whose structure/emotion is strongly outside the calibrated cohort’s sweet-spot.

**Important:**  
These labels are **advisory, not prescriptive**. They help producers and A&Rs read the number in context, but the judgment remains creative and human.

---

## 7. How This Respects the Creative Intelligence Framework (CIF) and Historical Echoes

The Music Advisor system is built around the **Creative Intelligence Framework (CIF)** with layered roles (Historical Analyst, Sonic Architect, Cultural Decoder, Emotional Forecaster, Market Strategist, Creative Director).

HCI_v1 sits primarily at the intersection of:

- **Sonic Architect Layer**  
  → Encodes the six structural/emotional axes (tempo/runtime/energy/dance/valence/loudness) as a compact numeric fingerprint.

- **Market Strategist Layer**  
  → Uses calibration cohorts and z-score mapping to interpret that fingerprint in the context of a specific market slice (e.g., US Pop 2025Q4).

### 7.1 Why 1.0 is _not_ in conflict with Historical Echoes

The **Historical Echoes thesis** says:

> “Across decades, certain structural/emotional patterns recur; modern hits are echoes of earlier archetypes, and future hits will echo today’s.”

HCI_v1 does **not** claim:

- “There is a single, timeless top song at 1.0 and everyone else is below.”

Instead:

- Each **cohort** (e.g., US Pop 2025Q4) has its own calibrated distribution and its own apex tier.
- A value of `1.0` simply says:
  - “Within this cohort’s six-axis space, this track defines the **current apex anchor**.”
- When you eventually add cohorts for other eras (e.g., 1980s Pop, 2000s R&B, etc.), **each cohort can have its own apex anchors**.

In other words:

- **Historical Echoes live across cohorts**, not only at the apex.
- HCI_v1 is just one scalar summary that says: “How tightly does this track fit this cohort’s sweet-spot?”
- Echo analysis will additionally look at **pattern similarity** across axes, not just a single scalar.

### 7.2 Why having apex anchors actually strengthens the echo concept

A small set of tracks in the **0.90–1.00 Apex Anchor tier** serve as:

- **Reference vectors** for future modeling (e.g., “move this WIP closer to the Flowers / Don’t Start Now axis”).
- **Cohort calibration points**, ensuring that when you compare across decades, you’re always measuring relative to meaningful centers and tails.

Rather than contradicting Historical Echoes, the apex tier:

- Gives the CIF a **stable definition of “now”** in each cohort.
- Makes it easier to say:
  - _“This 2035 track is an echo of the 2020 `Blinding Lights` zone, which itself echoed some 1980s synth-pop archetypes.”_

---

## 8. Why We Do **Not** (Currently) Cap Below 1.0

We considered introducing a hard cap (e.g., 0.98) so that no track ever displays `1.0`. For v1.1 we **intentionally do not do this**, for several reasons:

1. **Standard practice:**  
   Many real-world scoring systems use a full scale with clipping:

   - Streaming “popularity” scores (0–100, with top tracks often at 100).
   - ML features scaled to [0,1] with clamping.
   - Credit / risk scores that allow max values.

2. **Interpretability:**  
   `1.0` is intuitive. Telling users that “0.98 is our real maximum” complicates explanation with **no real gain**.

3. **Honesty:**  
   Some tracks genuinely do sit ≥ ~2–2.5σ above the cohort mean on these axes. Refusing to acknowledge that by squashing everything below 1.0 would hide a **real tail phenomenon**.

4. **CIF alignment:**  
   The CIF benefits from having **clear apex anchors**. As long as we define 1.0 precisely:
   - It does **not** imply metaphysical perfection.
   - It does **not** contradict the idea of future or past echoes.
   - It simply marks “current apex within this cohort and this calibration.”

If at some future version the UX or communication around 1.0 becomes problematic, the calibration scheme can be updated to:

- Keep internal scores in [0,1] but **display** a capped range (e.g., 0.05–0.98).
- Or adopt a logistic or quantile-based mapping instead of a straight z-score.

For v1.1, the simple z-score + clipping scheme is preferred for transparency and mathematical clarity.

---

## 9. Legacy vs Canonical HCI Fields

In the repo you may see two flavors of `.hci.json`:

1. **Legacy calibrator output**

   ```json
   "HCI_v1": {
     "raw":   <legacy_raw_value>,
     "score": <legacy_calibrated_score>,
     "source": "pop_us_2025Q4_calibrated",
     ...
   }
   ```

2. **Canonical v1.1 output** (from `tools/hci_axes.py` + `hci_calibration.py`)

   ```json
   "audio_axes": [ ... ],
   "HCI_v1": {
     "HCI_v1_score":      <calibrated>,
     "HCI_v1_score_raw":  <raw_mean_of_axes>,
     "meta": {
       "energy_thresholds": [...],
       "dance_thresholds":  [...],
       "valence_thresholds":[...],
       "calibration": {
         "scheme":      "zscore_linear_v1",
         "raw_mean":    μ_raw,
         "raw_std":     σ_raw,
         "target_mean": μ_target,
         "target_std":  σ_target
       }
     }
   }
   ```

Going forward, **the canonical fields are**:

- `audio_axes`
- `HCI_v1.HCI_v1_score_raw`
- `HCI_v1.HCI_v1_score`
- `HCI_v1.meta.*`

Any future whitepapers or CIF documentation should treat these as the **source of truth**.

---

## 10. TL;DR for Whitepapers / Future Docs

- **HCI_v1** is a **6-axis, cohort-relative score** that compresses tempo/runtime/energy/dance/valence/loudness into a single scalar in [0, 1].
- Raw axes are computed using **Gaussian fits** for structural traits and **clamped 0–1 values** for emotional traits.
- Raw HCI_v1 is the **mean of the six axes**.
- We calibrate HCI_v1 using a **z-score linear transform** so that a chosen calibration cohort (e.g., 00_core_modern) has a defined target mean and spread.
- The final **HCI_v1_score is clipped to [0, 1]**.
- A score of `1.0` means:
  > “This track’s six-axis profile is ≥ ~2–2.5 standard deviations above the cohort mean; it sits in the Apex Anchor tier of this specific cohort and calibration.”
- This does **not** conflict with the Historical Echoes thesis; it actually strengthens it by:
  - Providing **concrete apex anchors** for each cohort.
  - Making it easier to track **echo patterns across eras** relative to those anchors.
- Qualitative tiers (Apex, Strong, Competitive, Niche, Out-of-Cohort) are layered on top of the numeric score for human interpretation.
- The Creative Intelligence Framework uses HCI_v1 as **one quantitative lens** among many; it is not intended as a universal, timeless “hit oracle,” but as a calibrated structural/emotional barometer inside a larger, historically aware system.
