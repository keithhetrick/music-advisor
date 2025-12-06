#!/usr/bin/env python3
"""
build_spine_master_tier2_modern_lanes_v1.py

Build Tier 2 lanes CSV from the Tier 2 master spine.
Tier 1 behavior/files remain untouched.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional

from shared.config.paths import get_spine_root

def safe_float(val: str) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def band_tempo(tempo: Optional[float]) -> str:
    if tempo is None:
        return ""
    t = tempo
    if t < 80:
        return "tempo_sub_80"
    elif t < 100:
        return "tempo_80_100"
    elif t < 120:
        return "tempo_100_120"
    elif t < 140:
        return "tempo_120_140"
    else:
        return "tempo_over_140"


def band_valence(valence: Optional[float]) -> str:
    if valence is None:
        return ""
    v = valence
    if v < 0.2:
        return "valence_very_low"
    elif v < 0.4:
        return "valence_low"
    elif v < 0.6:
        return "valence_mid"
    elif v < 0.8:
        return "valence_high"
    else:
        return "valence_very_high"


def band_energy(energy: Optional[float]) -> str:
    if energy is None:
        return ""
    e = energy
    if e < 0.2:
        return "energy_very_low"
    elif e < 0.4:
        return "energy_low"
    elif e < 0.6:
        return "energy_mid"
    elif e < 0.8:
        return "energy_high"
    else:
        return "energy_very_high"


def band_loudness(loudness: Optional[float]) -> str:
    if loudness is None:
        return ""
    l = loudness
    if l < -18:
        return "loudness_very_quiet"
    elif l < -14:
        return "loudness_quiet"
    elif l < -10:
        return "loudness_mid"
    elif l < -6:
        return "loudness_loud"
    else:
        return "loudness_very_loud"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tier 2 master lanes CSV from Tier 2 master spine.")
    parser.add_argument(
        "--master",
        default=str(get_spine_root() / "spine_master_tier2_modern_v1.csv"),
        help="Path to Tier 2 master CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(get_spine_root() / "spine_master_tier2_modern_lanes_v1.csv"),
        help="Output lanes CSV path.",
    )

    args = parser.parse_args()

    master_path = Path(args.master)
    out_path = Path(args.out)

    if not master_path.exists():
        raise SystemExit(f"[build_spine_master_tier2_modern_lanes_v1] Missing master CSV: {master_path}")

    print(f"[build_spine_master_tier2_modern_lanes_v1] Loading master from: {master_path}")

    with master_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_master_tier2_modern_lanes_v1] Empty CSV or missing header: {master_path}"
            )

        master_fields: List[str] = list(reader.fieldnames)
        lane_fields = ["has_audio", "tempo_band", "valence_band", "energy_band", "loudness_band"]

        fieldnames: List[str] = list(master_fields)
        for lf in lane_fields:
            if lf not in fieldnames:
                fieldnames.append(lf)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[build_spine_master_tier2_modern_lanes_v1] Writing lanes to: {out_path}")
        total_rows = 0
        audio_rows = 0

        with out_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            for master_row in reader:
                total_rows += 1
                row = {fn: master_row.get(fn, "") for fn in master_fields}

                tempo = safe_float(master_row.get("tempo"))
                loudness = safe_float(master_row.get("loudness"))
                valence = safe_float(master_row.get("valence"))
                energy = safe_float(master_row.get("energy"))

                has_audio = int(tempo is not None and loudness is not None and valence is not None)

                if has_audio:
                    audio_rows += 1
                    row["has_audio"] = 1
                    row["tempo_band"] = band_tempo(tempo)
                    row["valence_band"] = band_valence(valence)
                    row["energy_band"] = band_energy(energy)
                    row["loudness_band"] = band_loudness(loudness)
                else:
                    row["has_audio"] = 0
                    row["tempo_band"] = ""
                    row["valence_band"] = ""
                    row["energy_band"] = ""
                    row["loudness_band"] = ""

                writer.writerow(row)

    print(
        f"[build_spine_master_tier2_modern_lanes_v1] Done. "
        f"Wrote {total_rows} rows; {audio_rows} rows with has_audio=1."
    )


if __name__ == "__main__":
    main()
