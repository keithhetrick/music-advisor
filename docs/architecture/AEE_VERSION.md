# Creative Intelligence Framework (CIF) — AEE/HCI Freeze Card

This file **freezes the current production behavior** of the audio side of Music Advisor
as a named version of the **Audio Echo Engine (AEE)** and **Hit Confidence Index (HCI)**,
aligned with the CIF v1.2 technical whitepaper (draft).

It also records the presence of a **separate ML calibration layer** for soft axes
(Energy & Danceability) as **AEE_ML v0.1**, which is **additive only** and **not yet
wired into canonical HCI math**.

It is documentation + naming only. **No math or thresholds used in the canonical
HCI_v1 pipeline are changed here.**

---

## 1. Versions & Scope

- CIF document: **CIF v1.2 (draft)**
- Audio engine: **AEE v1.0 (audio-only KPI path)**
- Historical model inside AEE: **HEM v1.0**
- Public KPI: **HCI v1.0 (audio-only)**
- Lyric engine (future): **LEE (shadow / advisory only; not implemented here)**
- ML calibration layer (soft axes, sidecar only): **AEE_ML v0.1**
- Repo: `music-advisor`

Canonical lane & policy (per CIF v1.2):

- Canonical KPI lane: `radio_us`
- Advisory lanes: `radio_us`, `spotify` (reco only; not part of HCI math)
- Fusion weight β (audio vs lyric):
  - Today: **β = 1.0** → audio-only HCI
  - Post-LEE graduation (future policy): β = 0.5 (40/40 rule)
- Caps:
  - `c_audio = 0.58`
  - `c_lyric = 0.58` (reserved for future LEE)

> In this codebase, only **AEE → HCI (audio)** is implemented in the canonical KPI path.  
> The ML layer (**AEE_ML v0.1**) exists as an **experimental sidecar** that calibrates
> Energy/Danceability axes; it does **not** modify HCI_v1 outputs unless an explicit
> host-level policy chooses to use it.

---

## 2. What is “frozen” right now?

The following **behaviors are considered part of AEE v1.0 / HCI v1.0** and define the
canonical KPI behavior for `US_Pop_2025`:

### 2.1 Feature extraction (audio)

- Implemented by `tools/cli/ma_audio_features.py` (pipeline extractor; shim: `tools/ma_audio_features.py`).
- Produces a **flat top-level JSON** with:

  - `source_audio`
  - `sample_rate`
  - `duration_sec`
  - `tempo_bpm`
  - `key`
  - `mode`
  - `loudness_LUFS`
  - `energy`
  - `danceability`
  - `valence`

- These semantics are **frozen for v1.0**  
  → do not rename keys or change their meaning without a version bump.

### 2.2 Axis + HCI pipeline (AEE only, canonical path)

- Implemented by:

  - `tools/ma_simple_hci_from_features.py`
  - `tools/hci_axes.py` (if present)
  - `tools/ma_fit_hci_calibration_from_hitlist.py`
  - `tools/ma_benchmark_check.py`

- Uses the **six-axis audio engine** as described in CIF:

  - The six audio axes (TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence)
    are combined via the engine mean:
    - **EACM** — Equal-Axis Composite Mean (6-axis average).

- Aggregates into HCI via:

  - Cap at **c_audio = 0.58**.
  - With β = 1.0 (audio-only), current HCI is effectively:
    - `HCI_v1 = min(EACM_audio, c_audio)` in the `radio_us` canonical lane.

### 2.3 Calibration artifacts (canonical AEE/HCI)

- Benchmark truth (Core 50 spine):

  - `calibration/benchmark_truth.csv`  
    → 50 canonical songs with ground-truth axis bands, including:
    - `tempo_feel_bpm_truth`
    - `runtime_band_truth`
    - `loudness_lufs_band_truth`
    - `energy_band_truth`
    - `dance_band_truth`
    - `valence_band_truth`

- Hitlist reference (historical):

  - `calibration/hitlist_pop_us_2025_core_v1_1.csv`  
    → **not** a source of truth; used as a historical reference / “reality check”.

- HCI calibration JSON (canonical for US_Pop_2025):

  - `calibration/hci_calibration_pop_us_2025Q4.json`

Together, these pieces define **AEE v1.0 + HCI v1.0** for **US_Pop_2025** in the
canonical KPI path.

---

## 3. What is _not_ implemented here (but exists in CIF)?

Concepts present in the CIF v1.2 whitepaper but **not yet implemented** in this repo:

- **Lyric Echo Engine (LEE)** and **Lyric Echo Resonance (LER)**:

  - Six lyric axes, HLM, lyric bootstrap tests, etc.
  - Today: lyrics are advisory-only in CIF; in this repo, they are not wired into HCI.

- **Host-level services**:

  - Recommendation Rules Engine (RRE).
  - Decade Continuum Registry (DCR, `/dcr/era`).
  - Trend Snapshot layer and lane-specific recommendations.
  - Cards (Profile / Run / Environment) as first-class JSON artifacts.
  - Host-level policy that might select between baseline axes vs ML-calibrated axes.

- **Validation machinery** (as full code):

  - Bootstrap confidence intervals for HCI.
  - VIF / whitening audit pipeline.
  - DBI (Decadal Balance Index) reporting.

These belong to the **Host / CIF orchestration layer**, which will eventually sit
_above_ this repo. For now, this repo is the **Audio Extractor + AEE + HCI (audio)**
slice, with an additional **AEE_ML v0.1 calibration layer** that stays strictly
sidecar-only.

---

## 4. Design intent for this freeze

1. **Give today’s system a name**

   - “This pipeline” = **AEE v1.0 / HCI v1.0 (audio-only)** under **CIF v1.2**.
   - **AEE_ML v0.1** is a **calibration extension** to AEE v1.0, not a replacement.

2. **Avoid accidental logic drift**

   - Any future ML layer, new axes, or refactors should either:
     - Stay strictly within AEE v1.0 behavior and not alter canonical HCI outputs, or
     - Bump the version (e.g., `AEE v1.1`, `HCI v1.1`, `AEE_ML v0.2`) _and_ update
       this file + `tools/aee_version.py`.

3. **Prepare for separation** (future):

   - Later, the **Audio Intelligence piece** (AEE + AEE_ML) can move into its own repo
     as an **Audio Echo Engine / Audio Intelligence Engine service**, with Music Advisor
     acting as a **Host / UI** that calls it.
   - The current ML modules are already grouped such that separation is straightforward.

---

## 5. How to bump a version later (playbook)

If you make **any change that affects numeric HCI outputs** (for the same inputs), do this:

1. Update `tools/aee_version.py`:

   - Bump `AEE_VERSION`, `HCI_VERSION`, and possibly `CIF_VERSION`.

2. Update this `AEE_VERSION.md`:

   - Add/update a **Change Log** section describing what changed and why.

3. Re-run:

   - `tools/ma_benchmark_check.py` against `calibration/benchmark_truth.csv`.

4. Record:

   - Note which corpus/profile the change targets (e.g., `US_Pop_2025`).
   - Keep the previous version tags for reproducibility.

If you make **ML-only changes** (e.g., retraining Energy/Danceability models
without touching canonical HCI math):

- Bump an **ML-specific version tag** (e.g., `AEE_ML v0.1 → v0.2`).
- Update the ML section in this file and any manifest file
  (e.g., `calibration/aee_ml/aee_ml_manifest.json`).

---

## 6. Quick reference (current constants)

- `profile_id`: `US_Pop_2025`
- `canonical_lane`: `radio_us`
- `beta` (audio vs lyric): `1.0` (audio-only)
- `c_audio`: `0.58`
- `c_lyric`: `0.58` (future LEE)
- Seeds (planned per CIF): `{42, 314, 2718}`

These constants are also exposed in:

- `tools/aee_version.py` (machine-readable view)
- This file (human-readable view)

---

## 7. AEE_ML Calibration v0.1 — Energy & Danceability (Sidecar Only)

This section records the first ML calibration snapshot for the soft axes
**Energy** and **Danceability**. It is **sidecar-only** and **does not change**
canonical HCI_v1 behavior unless a host explicitly chooses to consume the ML
outputs.

### 7.1 Dataset (Core 50 benchmark)

- Truth CSV: `calibration/benchmark_truth.csv`
- Size: **50 canonical songs** (Core 50 spine across decades)
- Labels used for ML:

  - `energy_band_truth` ∈ {`lo`, `mid`, `hi`}
  - `dance_band_truth` ∈ {`lo`, `mid`, `hi`}

- Features source:

  - One `*.features.json` per song in `features_output/`
  - Feature keys used in this version:
    - `tempo_bpm`
    - `duration_sec`
    - `loudness_LUFS`
    - `energy`
    - `danceability`
    - `valence`

These 50 songs form the **Core 50** benchmark and are used both to:

- Evaluate the baseline AEE v1.0 axis logic, and
- Train / evaluate the AEE_ML v0.1 models for Energy & Danceability.

### 7.2 Baseline vs ML performance (Core 50, 1:1 allowlist)

Approximate baseline AEE v1.0 axis accuracy (pre-ML, from recent runs):

- TempoFit: ~0.78
- RuntimeFit: ~0.82
- LoudnessFit: ~0.78
- Valence: ~0.70
- **Energy**: ~0.44
- **Danceability**: ~0.40

AEE_ML v0.1 (logistic regression, Core 50, strict 1:1 allowlist):

- **Energy axis (ML)**

  - `n_total   = 50`
  - `n_correct = 27`
  - `accuracy  = 0.540`

  Confusion matrix (truth rows, predicted cols):

  - `lo` truth: 2 lo / 0 mid / 0 hi
  - `mid` truth: 1 lo / 12 mid / 9 hi
  - `hi` truth: 4 lo / 9 mid / 13 hi

- **Danceability axis (ML)**

  - `n_total   = 50`
  - `n_correct = 24`
  - `accuracy  = 0.480`

  Confusion matrix (truth rows, predicted cols):

  - `lo` truth: 3 lo / 1 mid / 3 hi
  - `mid` truth: 4 lo / 11 mid / 7 hi
  - `hi` truth: 5 lo / 6 mid / 10 hi

Summary:

- ML calibration **improves** the two softest axes:
  - Energy: ~0.44 → 0.54
  - Danceability: ~0.40 → 0.48
- Most confusion is between **mid** and **hi** bands, which aligns with
  human “borderline” disagreements; wild misclassifications (lo ↔ hi) are rare.

### 7.3 Model details and artifacts

- Model type: **Logistic regression (multinomial)**  
  (scikit-learn `LogisticRegression`, single task per axis)

- Targets:

  - `axis_energy` (predict `energy_band_truth`)
  - `axis_dance` (predict `dance_band_truth`)

- Serialization:

  - `calibration/aee_ml/axis_energy.pkl`
  - `calibration/aee_ml/axis_dance.pkl`
  - Manifest: `calibration/aee_ml/aee_ml_manifest.json`

- Sidecar outputs:

  - For each `*.features.json` in `features_output/`, the ML layer writes a matching
    `*.ml_axes.json` file under `calibration/aee_ml_outputs/` containing
    ML-calibrated band predictions, e.g.:

    ```json
    {
      "audio_name": "2020_the_weeknd__blinding_lights__album",
      "axes_ml": {
        "energy_band_ml": "hi",
        "dance_band_ml": "mid"
      },
      "model_meta": {
        "aee_ml_version": "0.1",
        "feature_keys": [
          "tempo_bpm",
          "duration_sec",
          "loudness_LUFS",
          "energy",
          "danceability",
          "valence"
        ]
      }
    }
    ```

  - Canonical axis values remain in the baseline outputs (e.g., HCI pipeline JSON);
    ML outputs are **additive** and clearly namespaced under `axes_ml`.

### 7.4 CLI workflow for AEE_ML v0.1

The intended UX for this ML snapshot is:

```bash

# 1) Train ML calibration models from Core 50 benchmark
python tools/ma_aee_ml_train.py \
  --truth calibration/benchmark_truth.csv \
  --root  features_output \
  --out-dir calibration/aee_ml

# 2) Apply models to all available feature files
python tools/ma_aee_ml_apply.py \
  --root features_output \
  --model-dir calibration/aee_ml \
  --out-dir calibration/aee_ml_outputs

# 3) Benchmark ML vs Core 50 truth (strict 1:1 allowlist)
python tools/ma_benchmark_check_ml.py \
  --truth calibration/benchmark_truth.csv \
  --ml-root calibration/aee_ml_outputs \
  --out calibration/aee_ml_reports/benchmark_ml.txt

```

- `ma_benchmark_check_ml.py` enforces a **1:1 allowlist** between
  `benchmark_truth.csv` and `*.ml_axes.json` files so that:

  - Every truth row is either:
    - Fully matched to a sidecar and evaluated, or
    - Reported as “missing ML”.
  - Extra, unlabeled ML sidecars (e.g., other songs you’ve processed) are listed
    as **“Tracks with ML sidecars but no matching truth row (unlabeled, not scored)”**.

### 7.5 Governance notes for AEE_ML v0.1

- AEE_ML v0.1 is an **experimental calibration layer**:

  - It does **not** change canonical HCI_v1 outputs.
  - It is intended to **patch leaks first** (Energy/Danceability) and to
    validate whether ML-based calibration meaningfully improves alignment with the
    benchmark truth.

- Path forward to strengthen the benchmark:

  - Freeze this Core 50 snapshot as `benchmark_truth_pop_us_2025_core_v1.csv`.
  - Add a new “Core+” calibration CSV (e.g.,
    `benchmark_truth_pop_us_2025_coreplus_v1.csv`) with additional labeled songs,
    focusing on:
    - 2010–2025 US Pop hits
    - Underrepresented bands (lo-energy bangers, mid-band hits, etc.)
  - Use the large set of unlabeled tracks (already in `calibration/aee_ml_outputs/`)
    as a **candidate pool** for future labeling waves.

---

_Status: Freeze of AEE v1.0 / HCI v1.0 (audio-only) plus documentation of
AEE_ML v0.1 (Energy & Danceability calibration, sidecar-only) for the
`music-advisor` repo._
