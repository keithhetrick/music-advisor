# Tempo Confidence Calibration (Essentia + Madmom)

Repeatable recipe to harvest and calibrate tempo confidence cutoffs on a benchmark set, then bake them into the pipeline. Assumes Python 3.11 venv at `.venv` with Essentia + Madmom installed.

## Paths and env

- Calibration audio: `CAL_ROOT="/Volumes/Sound Bank/***Workload***/REFERENCES/44.1kHz/MusicAdvisor_calibration_11.10.2025/benchmark_set_v1_1"`
- Scratch output for sidecars/CSV: `OUT_ROOT="/tmp/tempo_calibration"`
- Activate env: `source .venv/bin/activate`

## 1) Batch sidecar extraction (both backends)

```bash
mkdir -p "$OUT_ROOT"
find "$CAL_ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" \) | while read -r f; do
  stem=$(basename "$f")
  # Essentia
  .venv/bin/python tools/cli/tempo_sidecar_runner.py \
    --backend essentia \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.ess.json" \
    --verbose
  # Madmom
  .venv/bin/python tools/cli/tempo_sidecar_runner.py \
    --backend madmom \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.mm.json" \
    --verbose
done
```

## 1b) Librosa-only baseline (pipeline without sidecar)

Run the same set through the built-in librosa backend to compare against Essentia/Madmom. Writes distinct filenames alongside the sidecars.

```bash
find "$CAL_ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" \) | while read -r f; do
  stem=$(basename "$f")
  .venv/bin/python tools/cli/ma_audio_features.py \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.librosa.json" \
    --tempo-backend librosa \
    --force
done
```

## 2) Harvest raw scores to CSV (Essentia + Madmom + Librosa)

```bash
.venv/bin/python - <<'PY'
import json, glob, csv, os
OUT_ROOT = "/tmp/tempo_calibration"
rows = []
for path in glob.glob(os.path.join(OUT_ROOT, "*.json")):
    with open(path) as f:
        data = json.load(f)
    audio = data.get("source_audio") or os.path.splitext(os.path.basename(path))[0]
    backend = data.get("backend") or data.get("tempo_backend_detail") or data.get("tempo_backend")
    tempo = data.get("tempo") or data.get("tempo_bpm")
    raw_conf = data.get("tempo_confidence_score_raw") if "tempo_confidence_score_raw" in data else data.get("tempo_confidence_score")
    norm_conf = data.get("tempo_confidence_score")
    beats_count = data.get("beats_count") if "beats_count" in data else data.get("tempo_beats_count")
    rows.append({
        "audio": audio,
        "backend": backend,
        "tempo": tempo,
        "tempo_confidence_score_raw": raw_conf,
        "tempo_confidence_score_norm": norm_conf,
        "tempo_alternates": data.get("tempo_alternates"),
        "beats_count": beats_count,
    })

fieldnames = ["audio", "backend", "tempo", "tempo_confidence_score_raw", "tempo_confidence_score_norm", "tempo_alternates", "beats_count"]
with open("/tmp/tempo_conf_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print("wrote /tmp/tempo_conf_raw.csv", len(rows), "rows")
PY
```

- The glob over `OUT_ROOT/*.json` will pick up `*.ess.json`, `*.mm.json`, and `*.librosa.json` (plus any sidecar/pipeline outputs you drop there). Backend is inferred from `backend` or `tempo_backend_detail`.

## 3) Analyze distributions

Quick percentile view:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
df = pd.read_csv("/tmp/tempo_conf_raw.csv")
for backend in df.backend.dropna().unique():
    print("\n==", backend)
    s = df[df.backend==backend].tempo_confidence_score_raw.dropna()
    print(s.describe(percentiles=[0.05,0.1,0.5,0.9,0.95]))
PY
```

- Pick backend-specific cutoffs:
  - Essentia: low < X1, med X1–X2, high > X2; normalize by clipping linearly between X1/X2 to 0–1.
  - Madmom: low < Y1, med Y1–Y2, high > Y2; same normalization.
- Optionally compare librosa: use the librosa CSV to gauge baseline error or half/double rates versus ground truth and the sidecars.
- Optional: plot histograms in a notebook if you want visual confirmation.

Benchmarks on `benchmark_set_v1_1` (p5/p95):

- Essentia: p5≈0.93, p95≈3.63 → suggested label cuts low<1.10, med 1.10–3.20, high>3.20; normalize with lower=0.93, upper=3.63.
- Madmom: p5≈0.21, p95≈0.38 → suggested label cuts low<0.23, med 0.23–0.33, high>0.33; normalize with lower=0.21, upper=0.38.
- Librosa (baseline/conf mostly high): p5≈0.92, p95≈0.97 → optional label cuts low<0.93, med 0.93–0.95, high>0.95; normalize with lower=0.92, upper=0.97.

## 3b) Evaluate against ground truth

Compare estimated tempos to truth (`calibration/benchmark_truth_v1_1.csv`) and report accuracy/half/double counts:

```bash
python scripts/tempo_conf_eval.py \
  --conf /tmp/tempo_conf_raw.csv \
  --truth calibration/benchmark_truth_v1_1.csv
```

You’ll see per-backend median/mean abs error, within 3 bpm/3%, and half/double counts. Unmatched stems (if any) are printed for inspection.

- The pipeline now applies a guarded half/double resolver for low-confidence madmom/librosa tempos (<~0.30, tempo <80 or >180), switching to half/double if it yields higher internal confidence. Rerun the batches to capture any improvements.

## Reference datasets on disk

- Benchmark truth (100 tracks): `calibration/benchmark_truth_v1_1.csv` (tempo ground truth, metadata); older set: `calibration/benchmark_truth.csv`.
- Calibration set audio root used above: `/Volumes/Sound Bank/***Workload***/REFERENCES/44.1kHz/MusicAdvisor_calibration_11.10.2025/benchmark_set_v1_1`.
- Broader Billboard/core seeds (for future comparisons): see `data/core_1600_seed_billboard.csv` and enriched versions (`core_1600_with_spotify*.csv`) under `data/`.

## Full batch (all three backends) + harvest + eval

Run three terminals (or background jobs) to sweep the benchmark set:

Prep:

```bash
CAL_ROOT="/Volumes/Sound Bank/***Workload***/REFERENCES/44.1kHz/MusicAdvisor_calibration_11.10.2025/benchmark_set_v1_1"
OUT_ROOT="/tmp/tempo_calibration"
mkdir -p "$OUT_ROOT"
source .venv/bin/activate
```

Essentia:

```bash
find "$CAL_ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" \) | while read -r f; do
  stem=$(basename "$f")
  .venv/bin/python tools/cli/tempo_sidecar_runner.py \
    --backend essentia \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.ess.json" \
    --verbose
done
```

Madmom:

```bash
find "$CAL_ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" \) | while read -r f; do
  stem=$(basename "$f")
  .venv/bin/python tools/cli/tempo_sidecar_runner.py \
    --backend madmom \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.mm.json" \
    --verbose
done
```

Librosa baseline:

```bash
find "$CAL_ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" \) | while read -r f; do
  stem=$(basename "$f")
  .venv/bin/python tools/cli/ma_audio_features.py \
    --audio "$f" \
    --out "$OUT_ROOT/${stem}.librosa.json" \
    --tempo-backend librosa \
    --force
done
```

Harvest:

```bash
.venv/bin/python - <<'PY'
import json, glob, csv, os
OUT_ROOT = "/tmp/tempo_calibration"
rows = []
for path in glob.glob(os.path.join(OUT_ROOT, "*.json")):
    with open(path) as f:
        data = json.load(f)
    audio = data.get("source_audio") or os.path.splitext(os.path.basename(path))[0]
    backend = data.get("backend") or data.get("tempo_backend_detail") or data.get("tempo_backend")
    tempo = data.get("tempo") or data.get("tempo_bpm")
    raw_conf = data.get("tempo_confidence_score_raw") if "tempo_confidence_score_raw" in data else data.get("tempo_confidence_score")
    norm_conf = data.get("tempo_confidence_score")
    beats_count = data.get("beats_count") if "beats_count" in data else data.get("tempo_beats_count")
    rows.append({
        "audio": audio,
        "backend": backend,
        "tempo": tempo,
        "tempo_confidence_score_raw": raw_conf,
        "tempo_confidence_score_norm": norm_conf,
        "tempo_alternates": data.get("tempo_alternates"),
        "beats_count": beats_count,
    })
fieldnames = ["audio", "backend", "tempo", "tempo_confidence_score_raw", "tempo_confidence_score_norm", "tempo_alternates", "beats_count"]
with open("/tmp/tempo_conf_raw.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader(); writer.writerows(rows)
print("wrote /tmp/tempo_conf_raw.csv", len(rows), "rows")
PY
```

Evaluate:

```bash
.venv/bin/python scripts/tempo_conf_eval.py \
  --conf /tmp/tempo_conf_raw.csv \
  --truth calibration/benchmark_truth_v1_1.csv
```

## 4) Bake thresholds

- `adapters/confidence_adapter.py`: add backend branches for Essentia (X1/X2) and Madmom (Y1/Y2) to map raw → normalized 0–1 and derive labels.
- `tools/cli/ma_audio_features.py` (`normalize_external_confidence`; shim: `tools/ma_audio_features.py`): mirror the same bounds (X1/X2, Y1/Y2); optional overrides via `--tempo-sidecar-conf-lower/--tempo-sidecar-conf-upper` or env if added.
- Keep raw `tempo_confidence_score_raw` in payloads for transparency.

## 5) Validate end-to-end

```bash
# Produce sidecars
.venv/bin/python tools/cli/tempo_sidecar_runner.py --backend madmom --audio <file> --out /tmp/test_mm.json
.venv/bin/python tools/cli/tempo_sidecar_runner.py --backend essentia --audio <file> --out /tmp/test_es.json

# Run extractor with sidecar
.venv/bin/python tools/cli/ma_audio_features.py \
  --audio <file> \
  --out /tmp/test.features.json \
  --external-tempo-json /tmp/test_mm.json \
  --tempo-backend sidecar \
  --force
```

Check `tempo_confidence_score_raw`, normalized `tempo_confidence_score`, and `tempo_confidence` label for each backend.

## 6) Document the numbers

- Record chosen cutoffs (X1/X2 for Essentia, Y1/Y2 for Madmom), normalization rule (linear between lower/upper, clipped), calibration set name/date.
- Update `docs/pipeline/README_ma_audio_features.md` (and/or `docs/calibration/README_CALIBRATION.md` and `COMMANDS.md`) when thresholds change.
- Note: running all three (Essentia, Madmom, and librosa) on the same benchmark set provides the richest comparison for calibration.
