# Music Advisor — Audio Calibration (US/Pop)

This document describes how to build and maintain a **stable, audio-only HCI baseline**.  
It uses **real-world hits** for anchors (calibration) and keeps **Trend** advisory-only.

## Why this matters

Calibration freezes what “centered” looks like for HCI scores. By pinning a baseline (e.g., `US_Pop_Cal_Baseline_2025Q4.json`), scores stay comparable across runs and quarters, and Trend/advisory overlays remain separate from the calibrated core. Without calibration discipline, HCI scores drift and become unreliable for diagnostics.

---

## Concepts

- **Calibration Set:** A curated set of proven hits (plus a few private “negatives”).  
  Used to compute reference distributions (means/σ, histograms) for audio axes.
- **Baseline:** A self-contained JSON (e.g., `US_Pop_Cal_Baseline_2025Q4.json`) containing
  tempo/runtime means and std, key histogram, and major/minor ratio. It does **not** include
  Trend. HCI should reference only this baseline.
- **Trend Layer:** A short half-life advisory bias for language and suggestions. Leave **OFF**
  during calibration; use for notes only after baseline is locked.
- **Testing vs Calibration:**
  - _Calibration_ builds a stable reference from known successes.
  - _Testing_ scores new/unknown songs against that reference to see if scores “feel right.”

---

## Folder layout

```mermaid

music-advisor/
calibration/
audio/ # put your calibration tracks here (WAV/AIFF/MP3)
datahub/
calibration/ # generated snapshots live here
cohorts/ # generated baselines live here
features_output/ # Automator results are written here
tools/
calib_coverage.py
make_calibration_snapshot.py
build_baseline_from_snapshot.py

```

## Step 0 — Prereqs / Quick sanity

```bash
cd ~/music-advisor
python -m pip install -e '.[audio,test]'
source .venv/bin/activate
```

Keep STRUCTURE_POLICY.use_ttc=false and use_exposures=false while calibrating.
Disable Goldilocks (advisory) during calibration passes.

Sanity check: run `make smoke` (1s tone) to verify Automator + merge + pack writer are intact; expect outputs in `features_output/<date>/tone/`.

Step 1 — Collect Audio
Place your curated High and Mid anchors (and a few private Negatives) in:

```bash
calibration/audio/
```

Tempo confidence calibration (Essentia/Madmom/Librosa): see `docs/tempo_conf_calibration.md` for the full batch + harvest + eval flow; quick eval command:

```bash
python scripts/tempo_conf_eval.py --conf /tmp/tempo_conf_raw.csv --truth calibration/benchmark_truth_v1_1.csv
```

Use legally obtained, high-quality files. Song list guidance is in your project notes;
the goal is broad coverage across tempo bands, mode (major/minor), and runtime.

Step 2 — Generate Packs (via Automator)
Run your Automator over the folder:

```bash
for f in calibration/audio/_.{wav,WAV,aiff,AIFF,mp3,MP3}; do
./automator.sh "$f"
done
```

This writes _.features.json, _.merged.json, \_.pack.json, and client payloads under:

```swift
features_output/YYYY/MM/DD/<SongName>/
```

Step 3 — Check Coverage
Use the coverage tool to ensure tempo × mode × runtime buckets are reasonably filled:

```bash
python tools/calib_coverage.py --root features_output --region US --profile Pop
```

This prints pivot counts and highlights empty cells you may want to fill.

Step 4 — Snapshot the Calibration Set
Create a versioned snapshot of all packs you want included:

```bash
python tools/make_calibration_snapshot.py \
 --root features_output \
 --region US --profile Pop \
 --out datahub/calibration/US_Pop_CalibrationSet_v1.json
```

Tip: Keep snapshot files small and curated. You can maintain v2, v3, etc.

Step 5 — Build the Baseline
Build a baseline from your snapshot:

```bash
python tools/build_baseline_from_snapshot.py \
 --snapshot datahub/calibration/US_Pop_CalibrationSet_v1.json \
 --region US --profile Pop
```

Outputs something like:

```bash
datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json

```

This file contains:

- tempo_bpm_mean, tempo_bpm_std
- runtime_sec_mean, runtime_sec_std
- key_distribution
- mode_ratio
- tempo_band_pref (top bands inferred from histogram)

Step 6 — Point the Loader at the New Baseline
Ensure your loader picks up the new file. You can either:

- Set BASELINE_COHORT_PATH=/absolute/path/to/.../US_Pop_Cal_Baseline_2025Q4.json, or

- Name the file US_Pop_Cal_Baseline_YYYYQX.json and let the loader auto-pick the latest.

Reinstall editable package if needed:

```bash
python -m pip install -e '.[audio,test]'
```

Step 7 — Smoke Test
Run a few songs (including your known “gold” test track) and confirm HCI feels right:

```bash
ma-pipe --audio path/to/song.wav --market 0.5 --emotional 0.5 --round 3 --out advisory.json
python - <<'PY'
import json; d=json.load(open("advisory.json")); print(json.dumps(d["HCI_v1"], indent=2))
PY

```

HCI should align with your expectations from the older system if the calibration set is solid.

Step 8 — Lock & Version

- Commit datahub/calibration/US_Pop_CalibrationSet_v1.json
- Commit datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json
- Tag your repo: git tag calib-us-pop-v1
- Document changes in your whitepaper addendum.

FAQ
Why not use a Spotify Top 50 (year-only) list?
Year-limited lists are trend-heavy and can skew axes. Use multi-year, proven hits for calibration; keep recent year leaders for Trend advisory, not the baseline.

How often do I update the baseline?
Rarely—only when you deliberately re-baseline. Otherwise, let it stand so HCI remains stable.

Can I add synthetic tracks (“manufactured bats”)?
Yes, sparingly—to fill sparse cells (e.g., slow/minor/long). They should not define the center.

Does Trend ever change HCI?
Not unless you explicitly re-weight. Keep Trend advisory-only for best stability.

## Axis Calibration — v1.1 (FROZEN)

This section documents the **frozen** calibration for the ENERGY and DANCE axes used by MusicAdvisor’s Audio Evaluation Engine (AEE).

### Canonical artifacts (v1.1)

These files are considered **ground truth** for v1.1 and should not be edited in-place:

- **Final truth labels (after manual review):**  
  `calibration/aee_ml_reports/truth_vs_ml_final_v1_1.csv`

- **Feature → band thresholds (derived from final truth):**  
  `calibration/aee_band_thresholds_v1_1_final.json`

The truth CSV contains:

- Per-track energy and danceability features
- Manually reviewed & finalized band labels:
  - `energy_truth` (lo / mid / hi)
  - `dance_truth` (lo / mid / hi)

The thresholds JSON encodes:

- `energy_feature`: lo / mid / hi cutpoints
- `danceability_feature`: lo / mid / hi cutpoints

These thresholds are computed from the distribution of the _features_ using the final truth CSV.

---

### How v1.1 was produced (reference)

Pipeline that led to the frozen calibration (run in this approximate order):

1. **Start from initial truth vs ML report**

   ```bash
   python tools/ma_truth_vs_ml_sanity.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_v1_1.csv \
     --top-n 25
   ```

2. **Compute initial feature-based thresholds**

   ```bash
   python tools/ma_band_thresholds_from_csv.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_v1_1.csv \
     --out calibration/aee_band_thresholds_v1_1.json
   ```

3. **Apply feature thresholds to generate band columns**

   ```bash
   python tools/ma_apply_axis_bands_from_thresholds.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_v1_1.csv \
     --out calibration/aee_ml_reports/truth_vs_ml_with_bands_v1_1.csv \
     --thresholds calibration/aee_band_thresholds_v1_1.json
   ```

4. **Triage disagreements between truth / ML / feature bands**

```bash
python tools/ma_truth_vs_ml_triage.py \
  --csv calibration/aee_ml_reports/truth_vs_ml_with_bands_v1_1.csv \
  --out calibration/aee_ml_reports/truth_vs_ml_triage_v1_1.csv
```

5. **Export triage buckets for inspection (optional helper)**

   ```bash
   python tools/ma_truth_vs_ml_export_buckets.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_triage_v1_1.csv
   ```

6. **Add manual-review support columns**

   ```bash
   python tools/ma_truth_vs_ml_add_review_columns.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_triage_v1_1.csv \
     --out calibration/aee_ml_reports/truth_vs_ml_review_v1_1.csv
   ```

7. **Manual review step (human-in-the-loop)**

   Open:

   - `calibration/aee_ml_reports/truth_vs_ml_review_v1_1.csv`

   and fill in / adjust:

   - `energy_truth_reviewed` (yes/no)
   - `energy_truth_corrected_band` (lo/mid/hi or blank)
   - `energy_truth_final_band`
   - `dance_truth_reviewed` (yes/no)
   - `dance_truth_corrected_band` (lo/mid/hi or blank)
   - `dance_truth_final_band`

   Then save the file.

8. **Finalize truth labels into a canonical CSV**

   ```bash
   python tools/ma_truth_vs_ml_finalize_truth.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_review_v1_1.csv \
     --out calibration/aee_ml_reports/truth_vs_ml_final_v1_1.csv
   ```

9. **Recompute thresholds from the finalized truth file**

   ```bash
   python tools/ma_band_thresholds_from_csv.py \
     --csv calibration/aee_ml_reports/truth_vs_ml_final_v1_1.csv \
     --out calibration/aee_band_thresholds_v1_1_final.json
   ```

10. **Sanity check (final)**

    ```bash
    python tools/ma_truth_vs_ml_sanity.py \
      --csv calibration/aee_ml_reports/truth_vs_ml_final_v1_1.csv \
      --top-n 25 \
      --thresholds calibration/aee_band_thresholds_v1_1_final.json
    ```

---

### How to use these in the pipeline

At runtime, the AEE should:

1. Load `aee_band_thresholds_v1_1_final.json` once at startup.
2. For each track, compute:

   ```python
   from tools.aee_band_thresholds import AxisThresholds, band_from_value

   thresholds = AxisThresholds.load(
       "calibration/aee_band_thresholds_v1_1_final.json"
   )

   energy_band = band_from_value(
       value=features["energy_feature"],
       lo=thresholds.energy.lo,
       hi=thresholds.energy.hi,
   )

   dance_band = band_from_value(
       value=features["danceability_feature"],
       lo=thresholds.danceability.lo,
       hi=thresholds.danceability.hi,
   )
   ```

3. Use `energy_band` and `dance_band` as the **canonical axis bands** for:

   - HCI scoring
   - downstream analysis
   - prompts / reporting

4. Treat any ML-predicted bands (`*_ml_band`) as **diagnostic only** for future model retraining, not as source-of-truth.

---

### Versioning policy

- v1.1 is now **frozen**.
- Any future changes (more songs, different band definitions, etc.) should create:
  - a new truth CSV (e.g., `truth_vs_ml_final_v1_2.csv`)
  - a new thresholds JSON (e.g., `aee_band_thresholds_v1_2_final.json`)
- Never overwrite v1.1 artifacts; they serve as a stable baseline for comparisons and regression checks.
