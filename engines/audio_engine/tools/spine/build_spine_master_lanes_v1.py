#!/usr/bin/env python3
"""
Builds lane-ified Tier 1 master spine from spine_master_v1.csv.

Responsibilities:
- Copy all master columns as-is (year, artist, title, etc. untouched).
- Add / recompute:
    - has_audio
    - tempo_band
    - valence_band
    - energy_band
    - loudness_band

has_audio semantics (Tier 1 canonical):
- has_audio = 1 if tempo, valence, and loudness are all present and numeric.
- has_audio = 0 otherwise.

Lane tags are only computed when has_audio = 1, else left blank.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional


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
    """
    Loudness is typically negative in LUFS or dB.
    We treat:
        very_quiet < -18
        quiet      -18 to -14
        mid        -14 to -10
        loud       -10 to -6
        very_loud  > -6
    """
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
    parser = argparse.ArgumentParser(
        description="Build Tier 1 master lanes CSV from master spine."
    )
    parser.add_argument(
        "--master",
        required=True,
        help="Path to spine_master_v1.csv.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to output spine_master_v1_lanes.csv.",
    )

    args = parser.parse_args()

    master_path = Path(args.master)
    out_path = Path(args.out)

    if not master_path.exists():
        raise SystemExit(f"[build_spine_master_lanes_v1] Missing master CSV: {master_path}")

    print(f"[build_spine_master_lanes_v1] Loading master from: {master_path}")

    with master_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit(
                f"[build_spine_master_lanes_v1] Empty CSV or missing header: {master_path}"
            )

        master_fields: List[str] = list(reader.fieldnames)

        # Lane columns we want to guarantee exist (we'll compute or overwrite).
        lane_fields = [
            "has_audio",
            "tempo_band",
            "valence_band",
            "energy_band",
            "loudness_band",
        ]

        fieldnames: List[str] = list(master_fields)
        for lf in lane_fields:
            if lf not in fieldnames:
                fieldnames.append(lf)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[build_spine_master_lanes_v1] Writing lanes to: {out_path}")
        total_rows = 0
        audio_rows = 0

        with out_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            for master_row in reader:
                total_rows += 1

                # Copy all master fields as-is
                row = {fn: master_row.get(fn, "") for fn in master_fields}

                # Parse key audio features
                tempo = safe_float(master_row.get("tempo"))
                loudness = safe_float(master_row.get("loudness"))
                valence = safe_float(master_row.get("valence"))
                energy = safe_float(master_row.get("energy"))

                has_audio = int(
                    tempo is not None and loudness is not None and valence is not None
                )

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
        f"[build_spine_master_lanes_v1] Done. "
        f"Wrote {total_rows} rows; {audio_rows} rows with has_audio=1."
    )


if __name__ == "__main__":
    main()
