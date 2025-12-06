#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

BANDS = {"lo", "mid", "hi"}


def safe_load_json(path: Path | None, label: str, audio_name: str):
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not parse {label} JSON for {audio_name} at {path}: {e}")
        return {}


def find_best_path(root: Path, audio_name: str, suffix: str) -> Path | None:
    """
    Find the *latest* matching file for this audio_name and suffix.
    Example suffix: ".features.ml_axes.json" or ".features.json"
    """
    pattern = f"{audio_name}_*{suffix}"
    matches = list(root.rglob(pattern))
    if not matches:
        return None
    if len(matches) > 1:
        matches = sorted(matches)
        print(f"[WARN] {root.name.upper()}: multiple matches for {audio_name}, choosing {matches[-1]}")
    return matches[-1]


def extract_band_from_ml(ml_obj, axis_keyword: str) -> str:
    """
    Try very hard to find a 'lo'/'mid'/'hi' label for a given axis in an ML sidecar.
    axis_keyword: 'energy' or 'dance' (we also treat 'danceability' as dance).
    """
    if not isinstance(ml_obj, dict):
        return ""

    axis_kw = axis_keyword.lower()
    alt_kw = "danceability" if axis_kw == "dance" else axis_kw

    # ---- 1) Simple flat keys: energy_band_ml, energy_band, axis_energy_band, danceability_band, etc.
    for k, v in ml_obj.items():
        ks = k.lower()
        vs = str(v).lower()
        if "band" in ks and (
            axis_kw in ks
            or alt_kw in ks
            or ("axis_" + axis_kw) in ks
            or (axis_kw + "_axis") in ks
        ):
            if vs in BANDS:
                return vs

    # ---- 2) Axis-style nested dict:
    #   axis_energy = { "band": "mid", ... }
    #   axis_danceability = { "label": "hi", ... }
    for k, v in ml_obj.items():
        ks = k.lower()
        if (axis_kw in ks or alt_kw in ks) and isinstance(v, dict):
            for kk, vv in v.items():
                kks = kk.lower()
                vvs = str(vv).lower()
                if any(tag in kks for tag in ("band", "label", "pred", "class")) and vvs in BANDS:
                    return vvs

    # ---- 3) Probability dictionary:
    #   axis_energy = {"lo": 0.1, "mid": 0.6, "hi": 0.3}
    for k, v in ml_obj.items():
        ks = k.lower()
        if (axis_kw in ks or alt_kw in ks) and isinstance(v, dict):
            keys_lower = {str(kk).lower() for kk in v.keys()}
            band_keys = list(keys_lower & BANDS)
            if len(band_keys) >= 2:
                best_band = None
                best_val = None
                for kk, vv in v.items():
                    kk_low = str(kk).lower()
                    if kk_low in BANDS:
                        try:
                            val = float(vv)
                        except Exception:
                            continue
                        if best_val is None or val > best_val:
                            best_val = val
                            best_band = kk_low
                if best_band:
                    return best_band

    # ---- 4) Recursive search anywhere in the object, but still tied to the axis keyword.
    def recurse(obj, path_keys):
        if isinstance(obj, dict):
            for kk, vv in obj.items():
                kks = str(kk).lower()
                new_path = path_keys + [kks]

                # If the path suggests we're inside this axis and the field looks like a band label
                if (axis_kw in " ".join(new_path) or alt_kw in " ".join(new_path)):
                    vvs = str(vv).lower()
                    if any(tag in kks for tag in ("band", "label", "pred", "class")) and vvs in BANDS:
                        return vvs

                found = recurse(vv, new_path)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = recurse(item, path_keys)
                if found:
                    return found
        return ""

    band = recurse(ml_obj, [])
    return band or ""


def main():
    parser = argparse.ArgumentParser(
        description="Generate truth_vs_ml report by joining benchmark_truth with features and ML sidecars."
    )
    parser.add_argument(
        "--truth",
        default="calibration/benchmark_truth_v1_1.csv",
        help="Path to benchmark truth CSV.",
    )
    parser.add_argument(
        "--ml-root",
        default="calibration/aee_ml_outputs",
        help="Root directory containing *.features.ml_axes.json files.",
    )
    parser.add_argument(
        "--feat-root",
        default="features_output",
        help="Root directory containing *.features.json files.",
    )
    parser.add_argument(
        "--out",
        default="calibration/aee_ml_reports/truth_vs_ml_v1_1.csv",
        help="Output CSV path.",
    )
    args = parser.parse_args()

    truth_csv = Path(args.truth)
    ml_root = Path(args.ml_root)
    feat_root = Path(args.feat_root)
    out_csv = Path(args.out)

    rows_out = []

    with truth_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        truth_rows = list(reader)

    for row in truth_rows:
        audio_name = row["audio_name"]

        ml_path = find_best_path(ml_root, audio_name, ".features.ml_axes.json")
        feat_path = find_best_path(feat_root, audio_name, ".features.json")

        ml = safe_load_json(ml_path, "ML", audio_name)
        feats = safe_load_json(feat_path, "features", audio_name)

        energy_ml_band = extract_band_from_ml(ml, "energy")
        dance_ml_band = extract_band_from_ml(ml, "dance")

        out_row = {
            "audio_name": audio_name,
            "artist": row.get("artist", ""),
            "title": row.get("title", ""),
            "year": row.get("year", ""),

            "energy_truth": row.get("energy_band_truth", ""),
            "energy_ml": energy_ml_band,

            "dance_truth": row.get("dance_band_truth", ""),
            "dance_ml": dance_ml_band,

            "valence_truth": row.get("valence_band_truth", ""),

            "tempo_bpm": feats.get("tempo_bpm", ""),
            "duration_sec": feats.get("duration_sec", ""),
            "loudness_LUFS": feats.get("loudness_LUFS", ""),

            "energy_feature": feats.get("energy", ""),
            "danceability_feature": feats.get("danceability", ""),
            "valence_feature": feats.get("valence", ""),

            "notes": row.get("notes", ""),
        }

        rows_out.append(out_row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "audio_name",
        "artist",
        "title",
        "year",
        "energy_truth",
        "energy_ml",
        "dance_truth",
        "dance_ml",
        "valence_truth",
        "tempo_bpm",
        "duration_sec",
        "loudness_LUFS",
        "energy_feature",
        "danceability_feature",
        "valence_feature",
        "notes",
    ]

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"[OK] Wrote {len(rows_out)} rows to {out_csv}")


if __name__ == "__main__":
    main()
