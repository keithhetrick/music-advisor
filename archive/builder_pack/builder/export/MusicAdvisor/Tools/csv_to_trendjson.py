#!/usr/bin/env python3
# csv_to_trendjson.py — v1.3 (encoding fallback, header skip, excel guard, robust sniff)
import csv, json, sys, argparse, datetime, pathlib, io, re

COMMON_ALIASES = {
    "title": ["title","track","track_name","name","song","song_title"],
    "artist": ["artist","artists","artist_name","artist_names","primaryartist","artist_name_s"],
    "platform_id": ["id","track_id","spotify_id","spotify_track_id","videoid","video_id","apple_id","amg_track_id"],
    "url": ["url","external_url","spotify_url","track_url","link","href","weburl","web_url"],
    "isrc": ["isrc","isrc_code"],
    "release_date": ["release_date","album_release_date","released","release","date"],
    "explicit": ["explicit","is_explicit","explicitness"],
    "tags": ["tags","notes","genres","moods","labels","comments"]
}

def norm(s:str)->str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s.strip()).strip("_")

def decode_bytes(raw: bytes) -> str:
    # Try likely encodings
    for enc in ("utf-8-sig","utf-16","utf-16le","utf-16be","latin-1"):
        try:
            text = raw.decode(enc)
            if text.strip():
                return text
        except Exception:
            continue
    # Fallback with replacement
    return raw.decode("utf-8", errors="replace")

def is_probably_excel(raw: bytes) -> bool:
    return raw[:4] == b"PK\x03\x04"  # XLSX zip signature

def strip_leading_blanklines(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)

def sniff_dialect(text: str):
    sample = "\n".join(text.splitlines()[:200])
    # Prefer common delimiters if sniffer struggles
    for delim in [",", "\t", ";", "|"]:
        try:
            csv.Sniffer().sniff(sample, delimiters=[delim])
            return delim
        except Exception:
            continue
    # Last resort: comma
    return ","

def parse_csv(text: str, delim: str):
    f = io.StringIO(text)
    reader = csv.reader(f, delimiter=delim)
    rows = [r for r in reader if any(cell.strip() for cell in r)]  # drop empty rows
    if not rows: return [], []
    # Skip non-header garbage lines until we hit an alphabetic header row
    idx = 0
    while idx < len(rows) and not any(re.search(r"[A-Za-z]", c or "") for c in rows[idx]):
        idx += 1
    rows = rows[idx:]
    if not rows: return [], []
    headers = [norm(h) for h in rows[0]]
    data = []
    for r in rows[1:]:
        row = {}
        for i, h in enumerate(headers):
            if i < len(r): row[h] = r[i]
        data.append(row)
    return data, headers

def first_present(row, keys):
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return None

def guess_bool(v):
    if v is None: return None
    s = str(v).strip().lower()
    if s in ("true","t","yes","y","1","explicit"): return True
    if s in ("false","f","no","n","0","clean","not_explicit"): return False
    return None

def map_row(row, user_map):
    def get(key):
        if user_map.get(key):
            return row.get(user_map[key])
        return None
    title  = get("title")  or first_present(row, COMMON_ALIASES["title"])
    artist = get("artist") or first_present(row, COMMON_ALIASES["artist"])
    pid    = get("platform_id") or first_present(row, COMMON_ALIASES["platform_id"])
    url    = get("url")    or first_present(row, COMMON_ALIASES["url"])
    isrc   = get("isrc")   or first_present(row, COMMON_ALIASES["isrc"])
    rdate  = get("release_date") or first_present(row, COMMON_ALIASES["release_date"])
    explicit = get("explicit")
    if explicit is None: explicit = first_present(row, COMMON_ALIASES["explicit"])
    tags   = get("tags")   or first_present(row, COMMON_ALIASES["tags"])
    track = {
        "platform_id": pid,
        "url": url,
        "title": title,
        "artist": artist,
        "isrc": isrc,
        "release_date": rdate,
        "explicit": guess_bool(explicit),
        "notes": [t.strip() for t in (tags or "").split(",") if t.strip()]
    }
    return {k:v for k,v in track.items() if v not in (None,"",[])}

def main():
    p = argparse.ArgumentParser(description="Convert playlist CSV to MusicAdvisor trend JSON schema v1.3")
    p.add_argument("csv_path")
    p.add_argument("-o","--out", default=None)
    p.add_argument("--source", default="spotify")
    p.add_argument("--playlist", required=True)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    # Optional explicit column overrides (use normalized names, see --show-headers)
    p.add_argument("--col-title"); p.add_argument("--col-artist"); p.add_argument("--col-platform_id")
    p.add_argument("--col-url"); p.add_argument("--col-isrc"); p.add_argument("--col-release_date")
    p.add_argument("--col-explicit"); p.add_argument("--col-tags")
    p.add_argument("--show-headers", action="store_true", help="Print normalized headers and exit")
    args = p.parse_args()

    path = pathlib.Path(args.csv_path)
    raw = path.read_bytes()

    if is_probably_excel(raw):
        print("ERROR: File looks like an Excel .xlsx, not CSV. Re-export as CSV (UTF-8).", file=sys.stderr)
        sys.exit(2)

    text = decode_bytes(raw)
    text = strip_leading_blanklines(text)
    delim = sniff_dialect(text)
    if args.verbose: print(f"[csv] delimiter detected: {delim}", file=sys.stderr)

    data, headers = parse_csv(text, delim)
    if not data:
        print("ERROR: Could not parse CSV rows. Check encoding/delimiter or re-export as CSV (UTF-8).", file=sys.stderr)
        if args.verbose:
            print("[debug] First 3 lines:", file=sys.stderr)
            for i, line in enumerate(text.splitlines()[:3], 1):
                print(f"  {i:02d}: {line}", file=sys.stderr)
        sys.exit(3)

    if getattr(args, "show_headers", False):
        print("Normalized headers:", ", ".join(headers))
        sys.exit(0)

    user_map = {
        "title": args.col_title, "artist": args.col_artist, "platform_id": args.col_platform_id,
        "url": args.col_url, "isrc": args.col_isrc, "release_date": args.col_release_date,
        "explicit": args.col_explicit, "tags": args.col_tags
    }
    user_map = {k:v for k,v in user_map.items() if v}

    tracks, skipped = [], 0
    for idx, row in enumerate(data):
        tr = map_row(row, user_map)
        if tr.get("title") and tr.get("artist"):
            tracks.append(tr)
        else:
            skipped += 1
            if args.verbose and skipped <= 10:
                print(f"[skip] row {idx+2} missing title/artist — keys={list(row.keys())}", file=sys.stderr)

    payload = {
        "source": args.source,
        "playlist": args.playlist,
        "generated_at": datetime.date.today().isoformat(),
        "tracks": tracks
    }

    if args.verbose:
        print(f"[summary] rows={len(data)} kept={len(tracks)} skipped={skipped}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    out = pathlib.Path(args.out or path.with_suffix(".json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(tracks)} tracks")

if __name__ == "__main__":
    main()
