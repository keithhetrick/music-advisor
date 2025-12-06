import os, json, csv
import numpy as np
from .normalizer import encode_feature_vector, as_vector, build_norm_stats, zscore, vector_order

def load_reference_features(path_csv: str):
    rows, meta_rows = [], []
    with open(path_csv, "r", encoding="utf-8") as f:
        # robust csv: allow commas and blank lines
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        required = {"bpm","loudness_lufs","energy","danceability","valence","runtime_sec"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise RuntimeError(f"features.csv missing required columns. Found: {reader.fieldnames}")
        for r in reader:
            if not any((v or "").strip() for v in r.values()):
                continue
            feat = encode_feature_vector(r)
            x = as_vector(feat)
            rows.append(x)
            meta_rows.append({
                "ref_id": r.get("ref_id",""),
                "title": r.get("title",""),
                "artist": r.get("artist",""),
                "rhythm_profile": r.get("rhythm_profile",""),
                "genre": r.get("genre",""),
                "tags": [t.strip() for t in (r.get("tags","") or "").split(",") if t.strip()]
            })
    if not rows:
        raise RuntimeError(f"No data rows found in {path_csv}. Did the cohort builder run on an empty glob?")
    return np.vstack(rows), meta_rows

def attach_meta_scores(meta_rows, meta_json_path: str):
    if not os.path.exists(meta_json_path):
        return meta_rows
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta_obj = json.load(f)
    # attach by ref_id
    out = []
    for r in meta_rows:
        ref = r.get("ref_id")
        m = meta_obj.get(ref, {})
        r2 = dict(r)
        r2["HCI_v1"] = m.get("HCI_v1", None)
        r2["HEM"] = m.get("HEM", None)
        out.append(r2)
    return out

def build_index(csv_path: str, meta_json: str, out_npz: str):
    X, meta = load_reference_features(csv_path)
    meta = attach_meta_scores(meta, meta_json)
    stats = build_norm_stats(X)
    Xn = zscore(X, stats)
    centroid = np.mean(Xn, axis=0)

    cohort_hci = [float(r.get("HCI_v1")) for r in meta if isinstance(r.get("HCI_v1"), (int, float))]
    cohort_hci_mean = float(np.mean(cohort_hci)) if cohort_hci else 0.0
    cohort_hci_std  = float(np.std(cohort_hci))  if cohort_hci else 1.0

    os.makedirs(os.path.dirname(out_npz), exist_ok=True)
    np.savez_compressed(
        out_npz,
        X_ref=Xn,
        mean=stats["mean"],
        std=stats["std"],
        centroid=centroid,
        meta=np.array(meta, dtype=object),
        cohort_hci_mean=cohort_hci_mean,
        cohort_hci_std=cohort_hci_std,
        columns=np.array(vector_order(), dtype=object)
    )
