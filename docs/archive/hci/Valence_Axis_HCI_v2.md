# Valence Axis & HCI_v2 Notes

---

## A. Doc snippet for the new Valence axis

### 1) Short prose you can drop into CIF / repo docs

### Valence Axis (Audio-Only, v1.1)

Valence in the Audio Echo Engine is a 0–1 scalar that approximates the
“brightness” or “emotional uplift” of a recording using **audio-only**
features. It does **not** look at lyrics.

For each track we compute:

- `energy` (0–1): overall dynamic/intensity envelope.
- `danceability` (0–1): movement / groove.
- `tempo_bpm`: used as a weak bias around the US pop mean (~112 BPM).
- `mode`: major / minor (small bias only).
- `valence` (legacy feature): earlier estimator from the feature extractor.

We then construct a centered score and map it back into [0,1]:

- Center `energy`, `danceability`, and legacy `valence` around 0.5.
- Add a small tempo offset around 112 BPM (mid-up tempos → slightly brighter).
- Add a mild major/minor bias (major ≈ +0.08, minor ≈ –0.08).
- Combine:

  `score = 0.25*legacy + 0.25*energy + 0.35*dance + 0.05*tempo + mode_bias`

- Affine map around 0.5, clamp to [0,1].

This produces:

- Lower Valence (~0.40–0.50) for moody / low-groove ballads.
- Mid Valence (~0.50–0.60) for neutral / mixed tracks.
- Higher Valence (~0.60–0.75) for bright, groovy uptempo records.

Valence is **internally consistent**, transparent, and calibrated on the
100-song US Pop benchmark set. It is not a psychological measure; it is a
“historical-echo” audio brightness axis.

---

### 2) Code comment block (if you want to paste at top of `hci_axes.py`)

You already have detailed docstrings, but if you want a short header:

```python
hci_axes.py — canonical 6-axis computation for HCI_v1/HCI_v2.

Axes (all 0..1):

  0 TempoFit       – tempo vs. market norms (Gaussian around mean)
  1 RuntimeFit     – runtime vs. market norms
  2 Energy         – normalized 0–1 intensity
  3 Danceability   – normalized 0–1 movement / groove
  4 Valence        – audio brightness / uplift proxy:
                      blend of legacy valence, energy, danceability,
                      small tempo offset around ~112 BPM, and major/minor bias
  5 LoudnessFit    – LUFS vs. market-master loudness

Valence is deliberately simple and interpretable. It is not lyric sentiment,
but an audio-only “historical echo” axis calibrated on the 100-song US Pop
benchmark set.
```

---

## B. Inspect HCI_v2 behavior with the fixed Valence

You already rebuilt:

- `data/hci_v2_training_pop_us_2025Q4.csv`
- `data/hci_v2_training_eval_pop_us_2025Q4.csv` (34 rows matched to targets).

Here are two quick local checks you can run to see what v2 is doing now that Valence is real.

---

### 1) Check correlation between target and prediction

```bash
python - << 'PY'
import csv, math

path = "data/hci_v2_training_eval_pop_us_2025Q4.csv"
targets, preds = [], []
with open(path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        t = row.get("EchoTarget_v2")
        p = row.get("HCI_audio_v2_hat")
        if t not in (None, "", "NaN") and p not in (None, "", "NaN"):
            targets.append(float(t))
            preds.append(float(p))

n = len(targets)
mean_t = sum(targets)/n
mean_p = sum(preds)/n
cov = sum((t-mean_t)*(p-mean_p) for t,p in zip(targets,preds))/n
std_t = math.sqrt(sum((t-mean_t)**2 for t in targets)/n)
std_p = math.sqrt(sum((p-mean_p)**2 for p in preds)/n)
corr = cov/(std_t*std_p) if std_t>0 and std_p>0 else float('nan')

print("n:", n)
print("corr(EchoTarget_v2, HCI_audio_v2_hat):", corr)
PY
```

If `corr` is reasonably positive (e.g. 0.4+), v2 is at least tracking the target.

---

### 2) Quick look at axis ranges in eval file

```bash
python - << 'PY'
import csv

path = "data/hci_v2_training_eval_pop_us_2025Q4.csv"
axes = ["TempoFit","RuntimeFit","LoudnessFit","Energy","Danceability","Valence"]
vals = {a: [] for a in axes}

with open(path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        for a in axes:
            v = row.get(a)
            if v not in (None, "", "NaN"):
                vals[a].append(float(v))

for a in axes:
    arr = vals[a]
    if not arr:
        continue
    print(a, "min=", min(arr), "max=", max(arr))
PY
```

You should see that Valence spans roughly the same 0.40–0.76 range as in the corpus, confirming it’s flowing into v2 training correctly.

If you want deeper ML diagnostics later (feature importances, regression summary), we can do that too, but these two checks confirm “v2 sees Valence and is roughly sane.”

---

## C. How to overlay HCI_v2 on top of HCI_v1 (design only)

Given your philosophy (HCI_v1 is canonical; v2 is advisory), a clean design is:

1. **Keep HCI_v1 as canonical**

   - Keep `HCI_v1_score` + `HCI_v1_final_score` exactly as-is.

- They remain the official scalar used for tiers and for the client host.

2. **Compute HCI_v2 offline or as an optional step**

   - Use `hci_v2_training` to fit a model that predicts `EchoTarget_v2` from the 6 axes.
   - At runtime (or as a batch tool), add something like:

   ```json
   "HCI_audio_v2": {
     "hat": 0.73,
     "residual_vs_target": -0.05,
     "model_version": "v2_2025Q4_001"
   }
   ```

   to `.hci.json`.

3. **In client / rich prompt**

   - Keep using HCI_v1 for the “official” score and tiers.
   - Present HCI_v2 as a secondary overlay, e.g.:

     - `HCI_v1: 0.84 (WIP-A+)`
     - `HCI_v2: 0.78 (slightly below historical echo expectation based on the 6 axes)`

   - Make it clear it’s “model-based refinement,” not a replacement.

4. **Guardrails**

   - If HCI_v2 disagrees strongly (large residual), treat it as a “flag for review,” not a correction.
   - Never let v2 overwrite HCI_v1 in JSON; always store it under its own key (`HCI_audio_v2`).

5. **Implementation sketch**

   When we get there, it would likely be a new tool, e.g.:

   ```bash
   python tools/hci_v2_apply_model.py \
     --root features_output/2025/11/18 \
     --model data/hci_v2_model_2025Q4.pkl
   ```

   that reads axes from `.hci.json`, adds `HCI_audio_v2`, and leaves everything else intact.
