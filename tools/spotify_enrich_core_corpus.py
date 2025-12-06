#!/usr/bin/env python3
"""
spotify_enrich_core_corpus.py

Enrich a core Billboard-based corpus (e.g. ~1,600 songs: Top N per year)
with Spotify metadata using the Spotify Web API.

Input CSV (example: data/core_1600_seed_billboard.csv) must contain:
    - year
    - title
    - artist
    - year_end_rank   (or similar)

Output CSV:
    - Same columns as input, plus:
        spotify_id
        spotify_name
        spotify_artist
        spotify_album
        release_date
        track_popularity

Usage:

    cd ~/music-advisor

    python tools/spotify_enrich_core_corpus.py \
        --in data/core_1600_seed_billboard.csv \
        --out data/core_1600_with_spotify.csv \
        --market US

Notes:
  - This script respects rate limiting by sleeping when Spotify returns 429.
  - If a track cannot be found, spotify_* fields are left empty.
  - We attempt to be robust to "feat." / "featuring" etc. in artist strings.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, Any, Optional

from spotify_client import SpotifyClient, SpotifyClientError  # same dir (tools/)


def _strip_featuring(artist: str) -> str:
    """
    Strip common "featuring" markers from an artist string to get the
    primary artist for Spotify search.

    Examples:
      "Morgan Wallen Featuring ERNEST" -> "Morgan Wallen"
      "Artist feat. Someone"           -> "Artist"
      "Artist ft Someone"              -> "Artist"

    We *only* use this for search; we keep the original artist string
    in the CSV.
    """
    s = artist.strip()
    if not s:
        return s

    lower = s.lower()
    cut = len(s)

    # Order matters only for picking the earliest occurrence
    markers = [
        " featuring ",
        " feat. ",
        " feat ",
        " ft. ",
        " ft ",
        " with ",
    ]

    for m in markers:
        idx = lower.find(m)
        if idx != -1 and idx < cut:
            cut = idx

    cleaned = s[:cut].strip()
    return cleaned or s


def enrich_row(
    client: SpotifyClient,
    row: Dict[str, str],
    market: str = "US",
) -> Dict[str, Any]:
    """
    Given a CSV row with year/title/artist, call Spotify and attach metadata.
    """
    title = row.get("title") or row.get("Title") or ""
    artist_raw = row.get("artist") or row.get("Artist") or ""
    year_str = row.get("year") or row.get("Year") or ""

    title = title.strip()
    artist = artist_raw.strip()

    year: Optional[int] = None
    try:
        year = int(year_str)
    except Exception:
        year = None

    if not title or not artist:
        # Can't search meaningfully; return row unchanged with empty spotify fields
        row_out: Dict[str, Any] = dict(row)
        row_out.update(
            {
                "spotify_id": "",
                "spotify_name": "",
                "spotify_artist": "",
                "spotify_album": "",
                "release_date": "",
                "track_popularity": "",
            }
        )
        return row_out

    # Clean artist string for search (handle "featuring"/"feat."/etc.)
    artist_search = _strip_featuring(artist)

    try:
        # First attempt: title + cleaned artist + year (if we have one)
        result = client.search_track(
            title=title, artist=artist_search, year=year, market=market
        )

        # Fallback: if that fails and we had a year, retry without year.
        if result is None and year is not None:
            result = client.search_track(
                title=title, artist=artist_search, year=None, market=market
            )

    except SpotifyClientError as e:
        print(f"[WARN] Spotify error for {title} — {artist}: {e}")
        result = None
    except Exception as e:
        print(f"[WARN] Unexpected error for {title} — {artist}: {e}")
        result = None

    row_out = dict(row)
    if result is None:
        print(
            f"[INFO] No Spotify match for: {title} — {artist} ({year if year is not None else 'year=?'})"
        )
        row_out.update(
            {
                "spotify_id": "",
                "spotify_name": "",
                "spotify_artist": "",
                "spotify_album": "",
                "release_date": "",
                "track_popularity": "",
            }
        )
    else:
        print(
            f"[OK] {title} — {artist} ({year if year is not None else 'year=?'}) -> "
            f"{result['spotify_name']} — {result['spotify_artist']} [{result['spotify_id']}]"
        )
        row_out.update(
            {
                "spotify_id": result.get("spotify_id", ""),
                "spotify_name": result.get("spotify_name", ""),
                "spotify_artist": result.get("spotify_artist", ""),
                "spotify_album": result.get("spotify_album", ""),
                "release_date": result.get("release_date", ""),
                "track_popularity": result.get("track_popularity", ""),
            }
        )

    # Be polite to the API; small sleep to smooth out bursts
    time.sleep(0.1)
    return row_out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Enrich core Billboard corpus with Spotify metadata."
    )
    ap.add_argument(
        "--in",
        dest="input_csv",
        required=True,
        help="Input CSV path (Billboard core corpus).",
    )
    ap.add_argument(
        "--out",
        dest="output_csv",
        required=True,
        help="Output CSV path with Spotify metadata.",
    )
    ap.add_argument(
        "--market",
        default="US",
        help="Spotify market code (default: US).",
    )
    args = ap.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)

    if not input_path.exists():
        raise SystemExit(f"[ERROR] Input CSV not found: {input_path}")

    client = SpotifyClient()

    with input_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    if not rows:
        raise SystemExit("[ERROR] Input CSV is empty.")

    # Prepare writer with extended fieldnames
    fieldnames = list(rows[0].keys()) + [
        "spotify_id",
        "spotify_name",
        "spotify_artist",
        "spotify_album",
        "release_date",
        "track_popularity",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for idx, row in enumerate(rows, start=1):
            print(f"\n[ROW {idx}/{len(rows)}]")
            enriched = enrich_row(client, row, market=args.market)
            writer.writerow(enriched)

    print(f"\n[DONE] Wrote enriched corpus to {output_path}")


if __name__ == "__main__":
    main()
