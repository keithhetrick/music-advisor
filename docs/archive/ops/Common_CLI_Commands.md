# music-advisor — Common CLI Commands

## 0. Setup

```bash
cd ~/music-advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 1. HCI v1 — Axes, Calibration, Final Score

### 1.1 Compute axes for a single track (debug)

```bash
python tools/hci_axes.py \
  --features path/to/track/*.features.json \
  --market-norms calibration/market_norms_us_pop.json
```

### 1.2 Recompute final scores (benchmarks + WIPs)

```bash
# Benchmarks (anchors)
python tools/hci_final_score.py \
  --root features_output/2025/11/17 \
  --recompute

# WIPs
python tools/hci_final_score.py \
  --root features_output/2025/11/18 \
  --recompute
```

### 1.3 Report top tracks by final score

```bash
# Benchmarks
python tools/hci_report_scores.py \
  --root features_output/2025/11/17 \
  --role benchmark \
  --top-k 10 \
  --sort-by final

# WIPs
python tools/hci_report_scores.py \
  --root features_output/2025/11/18 \
  --role wip \
  --top-k 10 \
  --sort-by final
```

---

## 2. Valence / Axes Maintenance

### 2.1 Recompute axes for all tracks under a root

```bash
python - << 'PY'
from pathlib import Path
import json, sys

sys.path.insert(0, str(Path(".").resolve()))
from tools.hci_axes import compute_axes
from tools.ma_simple_hci_from_features import DEFAULT_MARKET_NORMS

def recompute_axes_for_root(root_str: str) -> None:
    root = Path(root_str)
    for hci_path in root.rglob("*.hci"):
        track_dir = hci_path.parent
        feat_files = list(track_dir.glob("*.features.json"))
        if not feat_files:
            continue

        with feat_files[0].open("r", encoding="utf-8") as f:
            feats = json.load(f)
        if "features_full" in feats:
            feats = feats["features_full"]

        axes_list = compute_axes(feats, DEFAULT_MARKET_NORMS)
        if len(axes_list) != 6:
            continue

        axes_dict = {
            "TempoFit":     axes_list[0],
            "RuntimeFit":   axes_list[1],
            "Energy":       axes_list[2],
            "Danceability": axes_list[3],
            "Valence":      axes_list[4],
            "LoudnessFit":  axes_list[5],
        }

        with hci_path.open("r", encoding="utf-8") as f:
            hci = json.load(f)

        hci["audio_axes"] = [
            axes_dict["TempoFit"],
            axes_dict["RuntimeFit"],
            axes_dict["Energy"],
            axes_dict["Danceability"],
            axes_dict["Valence"],
            axes_dict["LoudnessFit"],
        ]
        hci["axes"] = axes_dict

        with hci_path.open("w", encoding="utf-8") as f:
            json.dump(hci, f, indent=2)

# Benchmarks + WIPs (2025-11-17/18)
recompute_axes_for_root("features_output/2025/11/17")
recompute_axes_for_root("features_output/2025/11/18")
PY
```

---

## 3. Historical Echo Corpus

### 3.1 Build/refresh the 100-song corpus (anchors)

```bash
python tools/build_historical_echo_corpus.py \
  --root features_output/2025/11/17 \
  --out data/historical_echo_corpus_2025Q4.csv \
  --set-name 2025Q4_seed
```

### 3.2 Quick valence sanity check

```bash
python - << 'PY'
import csv
path = "data/historical_echo_corpus_2025Q4.csv"
vals = []
with open(path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        v = row.get("valence")
        if v not in (None, "", "NaN"):
            vals.append(float(v))
print("num rows:", len(vals))
print("min valence:", min(vals))
print("max valence:", max(vals))
print("sample:", vals[:10])
PY
```

---

## 4. HCI v2 — Training & Eval

### 4.1 Build training matrix (axes → EchoTarget_v2)

```bash
python tools/hci_v2_build_training_matrix.py \
  --targets-csv data/hci_v2_targets_pop_us_1985_2024.csv \
  --corpus-csv  data/historical_echo_corpus_2025Q4.csv \
  --out-csv     data/hci_v2_training_pop_us_2025Q4.csv
```

### 4.2 Evaluate training set (optional diagnostics)

```bash
python tools/hci_v2_eval_training.py \
  --train-csv data/hci_v2_training_pop_us_2025Q4.csv \
  --out data/hci_v2_training_eval_pop_us_2025Q4.csv
```

### 4.3 Quick Valence sanity check in v2 eval

```bash
python - << 'PY'
import csv
path = "data/hci_v2_training_eval_pop_us_2025Q4.csv"
vals = []
with open(path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        v = row.get("Valence")
        if v not in (None, "", "NaN"):
            vals.append(float(v))
print("num rows:", len(vals))
print("min Valence:", min(vals))
print("max Valence:", max(vals))
print("sample:", vals[:10])
PY
```
