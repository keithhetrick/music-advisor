#!/usr/bin/env python3
import argparse
import csv
import datetime
import re
from pathlib import Path

def norm(s: str) -> str:
    s = (s or "").lower()
    # strip brackets / quotes
    s = re.sub(r"[\[\]'\"()]", " ", s)
    # normalize & / feat
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"\b(feat\.?|featuring|with)\b", " ", s)
    # non-alphanum -> space
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def clean_title_for_match(title: str) -> str:
    t = title or ""
    # drop parenthetical
    t = re.sub(r"\([^)]*\)", "", t)
    # drop stuff after " - " (e.g., remaster tags)
    if " - " in t:
        t = t.split(" - ", 1)[0]
    return norm(t)

def load_ut_slice(path: Path, years, max_rank: int):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if years and row["year"] not in years:
                continue
            if max_rank:
                try:
                    rk = int(row["year_end_rank"])
                except Exception:
                    rk = None
                if rk is not None and rk > max_rank:
                    continue
            rows.append(row)
    return rows

def load_external_tracks(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-csv", required=True)
    ap.add_argument("--external-csv", required=True)
    ap.add_argument("--years", nargs="*", default=[])
    ap.add_argument("--max-rank", type=int, default=40)
    args = ap.parse_args()

    years = [str(y) for y in args.years] if args.years else []
    years_label = f"{years[0]}_{years[-1]}" if years else "all"

    ut_path = Path(args.target_csv)
    ext_path = Path(args.external_csv)

    ut_rows = load_ut_slice(ut_path, years, args.max_rank)
    ext_rows = load_external_tracks(ext_path)

    print(f"Target rows in slice : {len(ut_rows)}")
    print(f"External tracks rows : {len(ext_rows)}")

    # --- build external indexes ---
    by_id = {}
    by_key = {}

    for row in ext_rows:
        sid = (row.get("id") or "").strip()
        if sid:
            by_id[sid] = row

        artist_raw = row.get("artists") or row.get("artist_name") or ""
        title_raw  = row.get("name")    or row.get("track_name")  or ""
        key = f"{norm(artist_raw)}|{clean_title_for_match(title_raw)}"
        if key.strip("|"):
            by_key[key] = row

    matched = 0
    unmatched = []
    out_rows = []

    for t in ut_rows:
        ut_year  = t.get("year", "")
        ut_rank  = t.get("year_end_rank", "")
        ut_artist = t.get("artist", "")
        ut_title  = t.get("title", "")

        ut_sid = (t.get("spotify_id") or t.get("id") or "").strip()
        ut_key = f"{norm(ut_artist)}|{clean_title_for_match(ut_title)}"

        ext = None
        match_source = ""

        # 1) direct Spotify ID match
        if ut_sid and ut_sid in by_id:
            ext = by_id[ut_sid]
            match_source = "id"
        # 2) fuzzy artist/title match
        elif ut_key in by_key:
            ext = by_key[ut_key]
            match_source = "fuzzy"

        if not ext:
            unmatched.append((ut_year, ut_rank, ut_artist, ut_title))
            continue

        matched += 1

        tempo   = ext.get("tempo") or ""
        loud    = ext.get("loudness") or ""
        dance   = ext.get("danceability") or ""
        energy  = ext.get("energy") or ""
        valence = ext.get("valence") or ""
        dur_ms  = ext.get("duration_ms") or ext.get("duration") or ""

        out_rows.append({
            "year": ut_year,
            "year_end_rank": ut_rank,
            "artist": ut_artist,
            "title": ut_title,
            "spotify_id": ut_sid or ext.get("id", ""),
            "match_source": match_source,
            "ext_artist_raw": ext.get("artists", ""),
            "ext_title_raw": ext.get("name", ""),
            "tempo": tempo,
            "danceability": dance,
            "energy": energy,
            "loudness": loud,
            "valence": valence,
            "duration_ms": dur_ms,
        })

    print("\n=== OFFLINE SPOTIFY MATCH SUMMARY ===")
    print("Target rows in slice : ", len(ut_rows))
    print("Matched with external:", matched)
    print("Unmatched targets    :", len(unmatched))

    if unmatched:
        print("\n[WARN] Unmatched sample (up to 10):")
        for y, rk, a, t in unmatched[:10]:
            print(f" - {y} {a} - {t} (rank {rk})")

    out_dir = Path("calibration/spotify_offline") / years_label
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"spotify_audio_features_{years_label}_{ts}.csv"

    if out_rows:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
    else:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "year", "year_end_rank", "artist", "title",
                "spotify_id", "match_source",
                "ext_artist_raw", "ext_title_raw",
                "tempo", "danceability", "energy",
                "loudness", "valence", "duration_ms",
            ])

    print(f"\n[OK] Wrote {len(out_rows)} rows to {out_path}")

if __name__ == "__main__":
    main()
