#!/usr/bin/env python3
"""
Calibration validator & manifest builder (v1.0.1)

- Scans the calibration root (default from env MA_CALIBRATION_ROOT or ./calibration).
- Enforces file naming: "Artist - Title__YYYY__echo_YYYY_YY.ext" inside echo bins.
- Excludes 13_negative/ and optional/ from stats.
- Writes JSON manifest with bucket contents and counts.
- Exits nonzero on hard errors; prints an OK banner when safe to bake.

Usage:
  python tools/calibration_validator.py --root /path/to/calibration \
    --out /path/to/calibration_manifest_v1.0.1.json
"""

import argparse, json, re, sys
from pathlib import Path
from datetime import datetime
from ma_config.paths import get_calibration_root

ECHO_DIR_RE = re.compile(r"^\d{2}_echo_(\d{4})_(\d{2})$")
FNAME_RE = re.compile(
    r"^(?P<artist>.+)\s-\s(?P<title>.+)__(?P<year>\d{4})__(?P<echo>echo_\d{4}_\d{2})\.(?P<ext>wav|aiff|aif|mp3)$",
    re.IGNORECASE,
)

EXCLUDE_DIRS = {"13_negative", "optional"}
GOLDEN_DIR = "00_golden_set"

def scan(root: Path):
    root = root.resolve()
    if not root.exists():
        raise SystemExit(f"[ERR] Root not found: {root}")

    buckets = {}
    warnings = []
    errors = []

    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        name = p.name

        # Golden set: acceptance fixtures
        if name == GOLDEN_DIR:
            items = []
            for f in sorted(p.iterdir()):
                if f.is_file():
                    # Golden set is looser: "Artist - Title__YYYY.ext"
                    m = re.match(r"^(?P<artist>.+)\s-\s(?P<title>.+)__(?P<year>\d{4})\.(?P<ext>wav|aiff|aif|mp3)$", f.name, re.IGNORECASE)
                    if not m:
                        warnings.append(f"[GOLDEN] '{f.name}' doesn't match relaxed golden pattern; will include as-is.")
                        entry = {"path": str(f.relative_to(root)), "artist": None, "title": None, "year": None, "bucket": GOLDEN_DIR, "class": "golden"}
                    else:
                        entry = {
                            "path": str(f.relative_to(root)),
                            "artist": m["artist"].strip(),
                            "title": m["title"].strip(),
                            "year": int(m["year"]),
                            "bucket": GOLDEN_DIR,
                            "class": "golden",
                        }
                    items.append(entry)
            buckets[name] = items
            continue

        # Explicit excludes
        if any(name.startswith(ex) for ex in EXCLUDE_DIRS):
            # Keep listing for awareness, but mark excluded
            items = []
            for f in sorted(p.iterdir()):
                if f.is_file():
                    items.append({"path": str(f.relative_to(root)), "class": "excluded"})
            buckets[name] = items
            continue

        # Echo buckets
        mdir = ECHO_DIR_RE.match(name)
        if not mdir:
            # Nonstandard dir; mark note but include listing
            warnings.append(f"[SKIP] Unknown folder '{name}' (not echo/golden/negative/optional).")
            continue

        echo_start = int(mdir.group(1))
        echo_end2 = int(mdir.group(2))  # e.g., 89
        echo_end = int(str(echo_start)[:2] + str(echo_end2))  # 1985 + 89 -> 1989
        bucket_items = []

        for f in sorted(p.iterdir()):
            if not f.is_file():
                continue
            m = FNAME_RE.match(f.name)
            if not m:
                errors.append(f"[NAME] '{f.name}' does not match required pattern in '{name}'.")
                continue

            artist = m["artist"].strip()
            title = m["title"].strip()
            year = int(m["year"])
            echo_tag = m["echo"]
            # Cross-check echo tag matches folder window
            tag_ok = echo_tag == f"echo_{echo_start}_{str(echo_end)[-2:]}"
            if not tag_ok:
                errors.append(f"[ECHO TAG] '{f.name}' echo tag '{echo_tag}' does not match folder window echo_{echo_start}_{str(echo_end)[-2:]}.")
            # Year within window?
            if not (echo_start <= year <= echo_end):
                warnings.append(f"[YEAR] '{f.name}' year {year} is outside folder window {echo_start}-{echo_end} (verify release year vs peak year).")

            entry = {
                "path": str(f.relative_to(root)),
                "artist": artist,
                "title": title,
                "year": year,
                "bucket": name,
                "echo_window": [echo_start, echo_end],
                "class": "calibration",
            }
            bucket_items.append(entry)

        buckets[name] = bucket_items

    return buckets, warnings, errors

def summarize(buckets: dict):
    included = {k: v for k, v in buckets.items() if k not in EXCLUDE_DIRS and k != GOLDEN_DIR}
    counts = {k: len(v) for k, v in included.items()}
    total = sum(counts.values())
    return counts, total

def main():
    ap = argparse.ArgumentParser()
    default_root = get_calibration_root()
    default_out = default_root / "calibration_manifest_v1.0.1.json"
    ap.add_argument("--root", default=str(default_root))
    ap.add_argument("--out", default=str(default_out))
    args = ap.parse_args()

    root = Path(args.root)
    buckets, warnings, errors = scan(root)
    counts, total = summarize(buckets)

    manifest = {
        "version": "v1.0.1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": str(root),
        "policy": {
            "include_dirs": sorted([k for k in buckets.keys() if k not in EXCLUDE_DIRS and k != GOLDEN_DIR and ECHO_DIR_RE.match(k)]),
            "exclude_dirs": sorted(list(EXCLUDE_DIRS)),
            "golden_dir": GOLDEN_DIR,
            "naming_rule": "Artist - Title__YYYY__echo_YYYY_YY.ext (inside echo bins)",
            "release_year_rule": "Use release year (not peak year).",
        },
        "buckets": buckets,
        "counts": counts,
        "total_included_for_stats": total,
        "warnings": warnings,
        "errors": errors,
    }

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[OK] Wrote manifest: {outp} (included for stats: {total})")

    if warnings:
        print("\n[WARN] Review the following:")
        for w in warnings:
            print("  -", w)

    if errors:
        print("\n[ERR] Fix the following before baking stats:")
        for e in errors:
            print("  -", e)
        sys.exit(2)

    print("\n✅ Validation passed. Safe to bake μ/σ from listed echo bins.")
    sys.exit(0)

if __name__ == "__main__":
    main()
