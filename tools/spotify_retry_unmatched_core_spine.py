#!/usr/bin/env python3
"""
spotify_retry_unmatched_core_spine.py

Purpose
-------
Second-pass Spotify enrichment for core_spine rows that still have no
spotify_id. This script:

  1) Reads unmatched rows from historical_echo.db: core_spine
  2) Applies title + artist normalization heuristics:
       - Strip (Theme From "…") / (From "…") soundtrack tags
       - Split double A-sides on "/"
       - Strip "(Featuring …)" / "(Duet With …)" from artist
       - Simplify "x" / "X" collabs and "/"-separated artists
  3) Re-queries Spotify using SpotifyClient with these cleaned values
  4) Writes successful matches to an overrides CSV:

       data/core_spine_spotify_overrides.csv

These overrides are then applied to the base corpus via:

  python tools/spotify_apply_overrides_to_core_corpus.py \
    --base data/core_1600_with_spotify.csv \
    --overrides data/core_spine_spotify_overrides.csv \
    --out data/core_1600_with_spotify_patched.csv

…which you can re-import into historical_echo.db via:

  python tools/historical_echo_core_spine_import.py \
    --csv data/core_1600_with_spotify_patched.csv \
    --db  data/historical_echo/historical_echo.db \
    --reset-core
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.config.paths import get_core_spine_root, get_historical_echo_db_path
from spotify_client import SpotifyClient, SpotifyClientError


# ---------- Title normalization helpers ----------

SOUNDTRACK_PAREN_RE = re.compile(
    r'\s*\((?:Theme From|Love Theme From|From)\s+"[^"]*"\)\s*',
    flags=re.IGNORECASE,
)


def strip_soundtrack_parenthetical(title: str) -> str:
    """
    Strip '(Theme From "…")', '(Love Theme From "…")', '(From "…")' from the title.
    """
    t = SOUNDTRACK_PAREN_RE.sub("", title)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def split_double_a_side(title: str) -> List[str]:
    """
    Split double A-side titles like "Foolish Games/You Were Meant For Me"
    into ["Foolish Games", "You Were Meant For Me"].
    """
    if "/" not in title:
        return [title]
    parts = [p.strip() for p in title.split("/") if p.strip()]
    return parts or [title]


def build_title_candidates(title: str) -> List[str]:
    """
    Build a small list of candidate titles to try with Spotify search.

    Includes:
      - original title
      - stripped soundtrack version
      - each side of a slash-split title, with and without soundtrack tags
    """
    candidates = set()

    original = re.sub(r"\s+", " ", title).strip()
    candidates.add(original)

    stripped = strip_soundtrack_parenthetical(title)
    candidates.add(stripped)

    for base in split_double_a_side(title):
        base_clean = re.sub(r"\s+", " ", base).strip()
        candidates.add(base_clean)
        base_stripped = strip_soundtrack_parenthetical(base)
        candidates.add(base_stripped)

    # Remove empties and duplicates, keep reasonable ordering by length
    unique = [c for c in {c for c in candidates if c}]
    unique.sort(key=lambda s: (len(s), s.lower()))
    return unique


# ---------- Artist normalization helpers ----------

ARTIST_PAREN_FEAT_RE = re.compile(
    r"\s*\((?:Duet With|Featuring)\s+.*?\)",
    flags=re.IGNORECASE,
)


def strip_artist_parenthetical(artist: str) -> str:
    """
    Remove parenthetical "(Duet With …)" / "(Featuring …)" from artist string.
    """
    return ARTIST_PAREN_FEAT_RE.sub("", artist)


def strip_trailing_collab_words(artist: str) -> str:
    """
    Remove trailing 'Duet With …', 'Featuring …', 'With …' from artist string.
    """
    a = re.sub(r"\s+Duet With\s+.*$", "", artist, flags=re.IGNORECASE)
    a = re.sub(r"\s+Featuring\s+.*$", "", a, flags=re.IGNORECASE)
    a = re.sub(r"\s+With\s+.*$", "", a, flags=re.IGNORECASE)
    return a


def simplify_collab_separators(artist: str) -> str:
    """
    Simplify '/', ' x ', ' X ' style collab separators.

    Strategy:
      - If '/' present, keep only the first artist segment.
      - Replace ' x ' / ' X ' with a single space.
    """
    a = artist
    if "/" in a:
        a = a.split("/")[0].strip()
    a = re.sub(r"\s+[xX]\s+", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    return a


def normalize_artist(artist: str) -> str:
    """
    Produce a normalized artist string closer to Spotify's canonical primary artist.

    Examples:
      - "Patrick Swayze (Featuring Wendy Fraser)" -> "Patrick Swayze"
      - "Lita Ford (Duet With Ozzy Osbourne)"     -> "Lita Ford"
      - "Frankie J Featuring Baby Bash"          -> "Frankie J"
      - "Jordin Sparks Duet With Chris Brown"    -> "Jordin Sparks"
      - "Vanessa Williams/Brian McKnight"        -> "Vanessa Williams"
      - "G-Eazy x Bebe Rexha"                    -> "G-Eazy Bebe Rexha"
    """
    a = artist.strip()
    a = strip_artist_parenthetical(a)
    a = strip_trailing_collab_words(a)
    a = simplify_collab_separators(a)
    a = re.sub(r"\s+", " ", a).strip()
    return a


# ---------- DB / override helpers ----------


def fetch_unmatched_core_spine_rows(
    db_path: Path, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        sql = """
            SELECT year, year_end_rank, title, artist
            FROM core_spine
            WHERE spotify_id IS NULL OR spotify_id = ''
            ORDER BY year, year_end_rank
        """
        if limit is not None and limit > 0:
            sql += f" LIMIT {int(limit)}"
        rows = cur.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def load_existing_override_keys(path: Path) -> set[Tuple[int, str, str]]:
    """
    Return a set of (year, title, artist) tuples already present in the overrides CSV,
    so we don't duplicate them.
    """
    keys: set[Tuple[int, str, str]] = set()
    if not path.exists():
        return keys
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year_str = (row.get("year") or "").strip()
            title = (row.get("title") or "").strip()
            artist = (row.get("artist") or "").strip()
            if not year_str or not title or not artist:
                continue
            try:
                year = int(year_str)
            except ValueError:
                continue
            keys.add((year, title, artist))
    return keys


def ensure_overrides_csv(path: Path) -> None:
    """
    Ensure the overrides CSV exists with the correct header.
    If the file already exists and is non-empty, leave it alone.
    """
    if path.exists():
        # If non-empty, assume it has a header already.
        if path.stat().st_size > 0:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "title", "artist", "spotify_id"])
    print(f"[INFO] Created overrides CSV with header: {path}")


# ---------- Spotify search logic ----------


def try_spotify_search_for_row(
    client: SpotifyClient,
    year: int,
    title: str,
    artist: str,
) -> Optional[Dict[str, Any]]:
    """
    Attempt a Spotify search for a given (year, title, artist) using
    normalized title/artist candidates. Returns a metadata dict on
    success or None if no confident match is found.
    """
    title_candidates = build_title_candidates(title)
    artist_clean = normalize_artist(artist)
    artist_variants = [artist_clean]

    # Also consider original artist as a fallback if it's different
    artist_original = re.sub(r"\s+", " ", artist).strip()
    if artist_original and artist_original != artist_clean:
        artist_variants.append(artist_original)

    # We'll try several search strategies in order of strictness:
    # 1) (candidate_title, artist_clean, year)
    # 2) (candidate_title, artist_clean, None)
    # 3) (candidate_title, None, year)
    # 4) (candidate_title, None, None)
    strategies = []

    for t in title_candidates:
        for a in artist_variants:
            strategies.append((t, a, year))
            strategies.append((t, a, None))
        strategies.append((t, None, year))
        strategies.append((t, None, None))

    tried = set()
    for t, a, y in strategies:
        key = (t.lower(), (a or "").lower(), y)
        if key in tried:
            continue
        tried.add(key)

        try:
            meta = client.search_track(title=t, artist=a, year=y)
        except SpotifyClientError as e:
            # Log and continue to next strategy
            print(
                f"[WARN] SpotifyClientError for title='{t}', artist='{a}', year={y}: {e}"
            )
            continue
        except Exception as e:
            print(
                f"[WARN] Unexpected error for title='{t}', artist='{a}', year={y}: {e}"
            )
            continue

        if not meta:
            continue

        spotify_id = meta.get("spotify_id")
        if not spotify_id:
            continue

        return meta

    return None


def append_overrides(
    overrides_path: Path, rows: List[Dict[str, Any]], client: SpotifyClient
) -> int:
    """
    For each unmatched row, try Spotify search and append successful
    matches to the overrides CSV.
    """
    ensure_overrides_csv(overrides_path)
    existing_keys = load_existing_override_keys(overrides_path)

    appended = 0
    with overrides_path.open("a", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)

        for idx, row in enumerate(rows, start=1):
            year = row.get("year")
            title = row.get("title", "").strip()
            artist = row.get("artist", "").strip()
            year_end_rank = row.get("year_end_rank")

            if year is None or title == "" or artist == "":
                print(f"[WARN] Skipping row {idx}: missing year/title/artist: {row}")
                continue

            try:
                year_int = int(year)
            except ValueError:
                print(f"[WARN] Skipping row {idx}: invalid year '{year}'")
                continue

            key = (year_int, title, artist)
            if key in existing_keys:
                print(
                    f"[INFO] Row already has override, skipping: "
                    f"{year_int} | {title} | {artist}"
                )
                continue

            print(
                f"[ROW {idx}] Trying Spotify retry for: "
                f"{year_int} | {year_end_rank} | {title} — {artist}"
            )

            meta = try_spotify_search_for_row(
                client=client, year=year_int, title=title, artist=artist
            )
            if not meta:
                print(
                    f"[MISS] No confident Spotify match for: {title} — {artist} ({year_int})"
                )
                continue

            spotify_id = meta.get("spotify_id")
            spotify_name = meta.get("spotify_name", "")
            spotify_artist = meta.get("spotify_artist", "")
            print(
                f"[OK] {title} — {artist} ({year_int}) -> "
                f"{spotify_name} — {spotify_artist} [{spotify_id}]"
            )

            writer.writerow([year_int, title, artist, spotify_id])
            existing_keys.add(key)
            appended += 1

    print(f"[DONE] Appended {appended} override row(s) to {overrides_path}")
    return appended


# ---------- CLI entrypoint ----------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Retry Spotify matching for unmatched core_spine rows in historical_echo.db "
            "using regex/naming heuristics and append successful matches to "
            "core_spine_spotify_overrides.csv."
        )
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=str(get_historical_echo_db_path()),
        help="Path to historical_echo.db (default honors MA_DATA_ROOT).",
    )
    parser.add_argument(
        "--overrides",
        dest="overrides_path",
        default=str(get_core_spine_root() / "core_spine_spotify_overrides.csv"),
        help="Path to overrides CSV (default: core_spine_spotify_overrides.csv under private/local_assets/core_spine).",
    )
    parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=None,
        help="Optional limit on number of unmatched rows to process.",
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    overrides_path = Path(args.overrides_path)

    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")

    unmatched_rows = fetch_unmatched_core_spine_rows(db_path, limit=args.limit)
    if not unmatched_rows:
        print("[INFO] No unmatched core_spine rows found (all have spotify_id).")
        return

    print(f"[INFO] Found {len(unmatched_rows)} unmatched core_spine rows to retry.")

    client = SpotifyClient()
    append_overrides(overrides_path, unmatched_rows, client)


if __name__ == "__main__":
    main()
