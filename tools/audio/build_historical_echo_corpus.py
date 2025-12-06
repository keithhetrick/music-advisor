#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ma_config.audio import resolve_hci_v2_corpus

# Import the canonical axis computation from the sibling module in tools/.
# This ensures the corpus always reflects the *current* 6-axis definition,
# including the updated Valence axis.
from hci_axes import compute_axes


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_market_norms() -> Dict[str, Any]:
    """
    Load the US Pop market norms used for TempoFit / RuntimeFit / LoudnessFit.

    This keeps the corpus aligned with the same norms the runtime uses.
    """
    from ma_config.audio import resolve_market_norms

    norms_path, cfg = resolve_market_norms(None, log=lambda *_args, **_kwargs: None)
    if cfg:
        return cfg
    root = Path(__file__).resolve().parent.parent
    norms_path = norms_path or (root / "calibration" / "market_norms_us_pop.json")
    with norms_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_slug_parts(slug: str) -> Tuple[str, str, str]:
    """
    Expect slugs like:
      2023_miley_cyrus__flowers__album
      2025_alex_warren__ordinary__single

    Returns (year, artist, title). If parsing fails, we fall back to
    best-effort splits so the corpus is still usable.
    """
    year = ""
    artist = ""
    title = ""

    if not slug:
        return year, artist, title

    # Try to peel off a leading 4-digit year.
    parts = slug.split("_", 1)
    if parts and parts[0].isdigit() and len(parts[0]) == 4:
        year = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
    else:
        rest = slug

    # Now split on "__" for artist / title / rest (album/single flag).
    if "__" in rest:
        # e.g. "miley_cyrus__flowers__album"
        bits = rest.split("__")
        if len(bits) >= 1:
            artist = bits[0].replace("_", " ")
        if len(bits) >= 2:
            title = bits[1].replace("_", " ")
    else:
        # Best-effort: treat rest as title.
        title = rest.replace("_", " ")

    return year, artist, title


def extract_scores_from_hci(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Pull all currently relevant scores out of a .hci.json.

    This gives us:
      - hci_v1_score_raw      (pre-calibration audio)
      - hci_v1_score          (calibrated audio)
      - hci_v1_final_score    (role-aware final)
      - hci_audio_v2_raw      (experimental v2 raw audio)
    """
    out: Dict[str, Optional[float]] = {
        "hci_v1_score_raw": None,
        "hci_v1_score": None,
        "hci_v1_final_score": None,
        "hci_audio_v2_raw": None,
    }

    # v1 raw and calibrated
    if "HCI_v1_score_raw" in data:
        try:
            out["hci_v1_score_raw"] = float(data["HCI_v1_score_raw"])
        except Exception:
            pass

    if "HCI_v1_score" in data:
        try:
            out["hci_v1_score"] = float(data["HCI_v1_score"])
        except Exception:
            pass

    # Some older snapshots may nest v1 scores under HCI_v1 dict.
    hci1 = data.get("HCI_v1")
    if isinstance(hci1, dict):
        if out["hci_v1_score_raw"] is None and "raw" in hci1:
            try:
                out["hci_v1_score_raw"] = float(hci1["raw"])
            except Exception:
                pass
        if out["hci_v1_score"] is None and "score" in hci1:
            try:
                out["hci_v1_score"] = float(hci1["score"])
            except Exception:
                pass

    # Audio v2 raw (experimental)
    audio_v2 = data.get("HCI_audio_v2")
    if isinstance(audio_v2, dict) and "raw" in audio_v2:
        try:
            out["hci_audio_v2_raw"] = float(audio_v2["raw"])
        except Exception:
            pass

    # Final score (role-aware)
    if "HCI_v1_final_score" in data:
        try:
            out["hci_v1_final_score"] = float(data["HCI_v1_final_score"])
        except Exception:
            pass
    else:
        hci2 = data.get("HCI_v1")
        if isinstance(hci2, dict) and "final_score" in hci2:
            try:
                out["hci_v1_final_score"] = float(hci2["final_score"])
            except Exception:
                pass

    return out


def extract_metadata_from_hci(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Pull non-numeric metadata that is useful for echo / debugging.
    """
    region = data.get("region")
    profile = data.get("profile")
    baseline_id = data.get("MARKET_NORMS_baseline_id")

    role = data.get("HCI_v1_role")
    if not role:
        hci = data.get("HCI_v1") or {}
        if isinstance(hci, dict):
            role = hci.get("role")

    return {
        "region": region,
        "profile": profile,
        "market_baseline_id": baseline_id,
        "hci_role": role,
    }


def compute_axes_for_track(
    track_dir: Path, market_norms: Dict[str, Any]
) -> Optional[Dict[str, float]]:
    """
    Given a track directory under features_output/... which contains:
      - *.features.json

    Load features_full and compute the 6 canonical axes using hci_axes.compute_axes.

    This ensures the corpus always reflects the current Valence axis and other
    axis definitions, independent of what was previously stored inside the .hci.
    """
    feat_files = list(track_dir.glob("*.features.json"))
    if not feat_files:
        return None

    feat_path = feat_files[0]
    try:
        feats = load_json(feat_path)
    except Exception:
        return None

    if "features_full" in feats:
        feats_full = feats["features_full"]
    else:
        feats_full = feats

    axes_list = compute_axes(feats_full, market_norms)

    if not isinstance(axes_list, (list, tuple)) or len(axes_list) != 6:
        return None

    return {
        "TempoFit": float(axes_list[0]),
        "RuntimeFit": float(axes_list[1]),
        "Energy": float(axes_list[2]),
        "Danceability": float(axes_list[3]),
        "Valence": float(axes_list[4]),
        "LoudnessFit": float(axes_list[5]),
    }


def collect_rows(
    root: Path,
    set_name: str,
    mark_calibration: bool,
    mark_echo: bool,
    market_norms: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for hci_path in root.rglob("*.hci.json"):
        try:
            data = load_json(hci_path)
        except Exception as e:
            print(f"[WARN] Failed to read {hci_path}: {e}")
            continue

        track_dir = hci_path.parent
        slug = track_dir.name
        year, artist, title = parse_slug_parts(slug)

        axes = compute_axes_for_track(track_dir, market_norms)
        if axes is None:
            continue

        scores = extract_scores_from_hci(data)
        meta = extract_metadata_from_hci(data)

        row: Dict[str, Any] = {
            "slug": slug,
            "year": year,
            "artist": artist,
            "title": title,
            "source_root": str(root),
            "set_name": set_name,
            "in_calibration_set": bool(mark_calibration),
            "in_echo_set": bool(mark_echo),
            "region": meta.get("region"),
            "profile": meta.get("profile"),
            "market_baseline_id": meta.get("market_baseline_id"),
            "hci_role": meta.get("hci_role"),
            "tempo_fit": axes.get("TempoFit"),
            "runtime_fit": axes.get("RuntimeFit"),
            "loudness_fit": axes.get("LoudnessFit"),
            "energy": axes.get("Energy"),
            "danceability": axes.get("Danceability"),
            "valence": axes.get("Valence"),
            "hci_v1_score_raw": scores.get("hci_v1_score_raw"),
            "hci_v1_score": scores.get("hci_v1_score"),
            "hci_v1_final_score": scores.get("hci_v1_final_score"),
            "hci_audio_v2_raw": scores.get("hci_audio_v2_raw"),
        }

        rows.append(row)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Historical Echo Corpus CSV from one or more features_output roots."
    )
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root(s) under features_output to scan (e.g. features_output/2025/11/17).",
    )
    parser.add_argument(
        "--out",
        required=False,
        default=None,
        help="Output CSV path (default honors env HCI_V2_CORPUS_CSV or data/historical_echo_corpus_2025Q4.csv).",
    )
    parser.add_argument(
        "--calibration-root",
        action="append",
        default=[],
        help="Which roots should be flagged as part of the calibration set.",
    )
    parser.add_argument(
        "--echo-root",
        action="append",
        default=[],
        help="Which roots should be flagged as part of the historical echo set.",
    )
    parser.add_argument(
        "--set-name",
        default="2025Q4_seed",
        help="Label for this corpus slice (e.g. '2025Q4_benchmark_100').",
    )

    args = parser.parse_args()
    out_path = resolve_hci_v2_corpus(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    market_norms = load_market_norms()

    all_rows: List[Dict[str, Any]] = []

    calib_roots = set(args.calibration_root or [])
    echo_roots = set(args.echo_root or [])

    for root_str in args.root:
        root = Path(root_str)
        mark_cal = root_str in calib_roots
        mark_echo = root_str in echo_roots

        print(f"[INFO] Scanning {root} (calibration={mark_cal}, echo={mark_echo})")
        rows = collect_rows(root, args.set_name, mark_cal, mark_echo, market_norms)
        all_rows.extend(rows)

    fieldnames = [
        "slug",
        "year",
        "artist",
        "title",
        "source_root",
        "set_name",
        "in_calibration_set",
        "in_echo_set",
        "region",
        "profile",
        "market_baseline_id",
        "hci_role",
        "tempo_fit",
        "runtime_fit",
        "loudness_fit",
        "energy",
        "danceability",
        "valence",
        "hci_v1_score_raw",
        "hci_v1_score",
        "hci_v1_final_score",
        "hci_audio_v2_raw",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"[OK] Wrote {len(all_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
