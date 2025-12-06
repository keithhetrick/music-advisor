from ma_audio_engine.adapters.bootstrap import ensure_repo_root
#!/usr/bin/env python3
"""
spotify_apply_overrides_to_core_corpus.py

Purpose
-------
Apply manual Spotify ID overrides to a core Billboard corpus that has
already been enriched via spotify_enrich_core_corpus.py, and write a
patched CSV with corrected Spotify metadata.

This version is intentionally "dumb and safe":

  * It does NOT import or use SpotifyClient.
  * It does NOT call get_track_by_id or any other Spotify API method.
  * It simply trusts the spotify_id values provided in the overrides CSV
    and applies them to matching rows in the base corpus.

Workflow
--------
1. Base corpus (enriched automatically):

     data/core_1600_with_spotify.csv
       - year,title,artist,year_end_rank,...
       - spotify_id,spotify_name,spotify_artist,spotify_album,
         release_date,track_popularity

2. Manual / retry overrides:

     data/core_spine_spotify_overrides.csv
       - at minimum: year,title,artist,spotify_id
       - may optionally include: spotify_name,spotify_artist,spotify_album,
         release_date,track_popularity

3. This script:
   - Loads base corpus into memory.
   - Loads overrides.
   - For each override:
       * Finds matching row(s) in base corpus by (year, title, artist).
       * Updates spotify_id in the matched row(s).
       * If the override row includes additional spotify_* fields, those
         are applied as well.
   - Writes a patched CSV, e.g.:

       data/core_1600_with_spotify_patched.csv

After that, you can re-import the patched CSV into historical_echo.db
via historical_echo_core_spine_import.py with --reset-core.

Usage
-----

  cd ~/music-advisor

  python tools/spotify_apply_overrides_to_core_corpus.py \
    --base data/core_1600_with_spotify.csv \
    --overrides data/core_spine_spotify_overrides.csv \
    --out data/core_1600_with_spotify_patched.csv
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ma_config.audio import resolve_hci_v2_targets

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso


def _norm(s: str) -> str:
    """
    Normalize strings for matching:
      - strip leading/trailing whitespace
      - collapse internal whitespace
      - lowercase
    """
    if s is None:
        return ""
    s = " ".join(s.strip().split())
    return s.lower()


def _build_key(year: int, title: str, artist: str) -> Tuple[int, str, str]:
    return (year, _norm(title), _norm(artist))


def load_base_corpus(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit(f"[ERROR] Base corpus CSV {path} is empty.")

    return rows


def load_overrides(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit(f"[ERROR] Overrides CSV {path} is empty.")

    # Expect at least: year,title,artist,spotify_id
    required = {"year", "title", "artist", "spotify_id"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise SystemExit(
            f"[ERROR] Overrides CSV {path} is missing required columns: {sorted(missing)}"
        )

    return rows


def apply_overrides(
    base_rows: List[Dict[str, Any]],
    override_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Apply overrides in-place and return updated rows.

    Matching strategy:
      - Index base corpus by (year, normalized title, normalized artist)
      - For each override row with (year, title, artist, spotify_id),
        update all matching rows in the base corpus.
    """
    # Build index from (year, norm_title, norm_artist) -> list of row indices
    index: Dict[Tuple[int, str, str], List[int]] = {}
    for i, row in enumerate(base_rows):
        year_str = (
            row.get("year")
            or row.get("Year")
            or row.get("chart_year")
            or row.get("chartYear")
            or ""
        )
        try:
            year = int(str(year_str).strip())
        except Exception:
            # If we can't parse year, skip indexing this row
            continue

        title = row.get("title") or row.get("Title") or ""
        artist = row.get("artist") or row.get("Artist") or ""
        key = _build_key(year, title, artist)

        index.setdefault(key, []).append(i)

    _log(f"[INFO] Built index for {len(index)} unique (year,title,artist) keys.")

    # Determine which optional spotify_* columns exist in base corpus
    base_fieldnames = set(base_rows[0].keys())
    optional_cols = [
        "spotify_name",
        "spotify_artist",
        "spotify_album",
        "release_date",
        "track_popularity",
    ]

    updated_count = 0

    for o_idx, o_row in enumerate(override_rows, start=1):
        year_str = (o_row.get("year") or o_row.get("Year") or "").strip()
        title = (o_row.get("title") or o_row.get("Title") or "").strip()
        artist = (o_row.get("artist") or o_row.get("Artist") or "").strip()
        spotify_id = (o_row.get("spotify_id") or "").strip()

        if not (year_str and title and artist and spotify_id):
            _log(
                f"[WARN] Override row {o_idx} missing required fields "
                f"(year/title/artist/spotify_id); skipping: {o_row}"
            )
            continue

        try:
            year = int(year_str)
        except Exception:
            _log(f"[WARN] Override row {o_idx} has invalid year '{year_str}'; skipping.")
            continue

        key = _build_key(year, title, artist)
        matches = index.get(key, [])

        if not matches:
            _log(
                f"[WARN] Override row {o_idx}: no base corpus match for "
                f"({year}, '{title}', '{artist}')."
            )
            continue

        _log(
            f"[INFO] Override {o_idx}: applying spotify_id={spotify_id} to "
            f"{len(matches)} matching base row(s) for "
            f"({year}, '{title}', '{artist}')."
        )

        for base_idx in matches:
            row = base_rows[base_idx]

            # Always set spotify_id
            row["spotify_id"] = spotify_id

            # If overrides CSV has extra spotify_* fields AND the base corpus
            # has those columns, propagate them too.
            for col in optional_cols:
                if col in base_fieldnames and col in o_row and o_row[col]:
                    row[col] = o_row[col]

            updated_count += 1

    _log(f"[DONE] Applied overrides to {updated_count} base row(s).")
    return base_rows


def write_patched_corpus(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        raise SystemExit("[ERROR] No rows to write in patched corpus.")

    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    _log(f"[DONE] Wrote patched corpus to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply manual Spotify ID overrides to core_1600_with_spotify.csv, "
            "without calling any Spotify API methods."
        )
    )
    parser.add_argument(
        "--base",
        dest="base_csv",
        required=False,
        default=None,
        help="Base enriched corpus CSV (default honors env HCI_V2_TARGETS_CSV or data/core_1600_with_spotify.csv).",
    )
    parser.add_argument(
        "--overrides",
        dest="overrides_csv",
        required=True,
        help="Overrides CSV (e.g., data/core_spine_spotify_overrides.csv).",
    )
    parser.add_argument(
        "--out",
        dest="out_csv",
        required=False,
        default=None,
        help="Output patched CSV (default aligns with base path name or env HCI_V2_TARGETS_CSV).",
    )
    parser.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    parser.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(parser)
    args = parser.parse_args()

    apply_log_sandbox_env(args)

    redact_env = os.getenv("LOG_REDACT", "0") == "1"
    redact_values_env = [v for v in (os.getenv("LOG_REDACT_VALUES") or "").split(",") if v]
    redact_flag = args.log_redact or redact_env
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or redact_values_env
    )
    global _log
    _log = make_logger("spotify_apply_overrides", use_rich=False, redact=redact_flag, secrets=redact_values)

    base_path = Path(args.base_csv) if args.base_csv else resolve_hci_v2_targets(None)
    overrides_path = Path(args.overrides_csv)
    out_path = Path(args.out_csv) if args.out_csv else base_path.with_name(base_path.stem + "_patched.csv")

    if not base_path.exists():
        raise SystemExit(f"[ERROR] Base CSV not found: {base_path}")
    if not overrides_path.exists():
        raise SystemExit(f"[ERROR] Overrides CSV not found: {overrides_path}")

    base_rows = load_base_corpus(base_path)
    overrides = load_overrides(overrides_path)

    updated_rows = apply_overrides(base_rows, overrides)
    write_patched_corpus(out_path, updated_rows)
    _log(f"[DONE] Finished at {utc_now_iso()}")


if __name__ == "__main__":
    main()
