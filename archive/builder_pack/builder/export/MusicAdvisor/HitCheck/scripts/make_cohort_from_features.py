import os, glob, json, csv, argparse

REQ_NUM = ["bpm","duration_sec","loudness_lufs","energy","danceability","valence"]

def coerce_num(v):
    if v is None: return None
    try:
        return float(v)
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser(description="Build features.csv/meta.json from per-track JSONs")
    ap.add_argument("--src", required=True, help="Glob for input JSON files (quoted)")
    ap.add_argument("--outdir", required=True, help="Output directory for cohort files")
    ap.add_argument("--prefix", default="hitlist", help="Ref-id prefix")
    args = ap.parse_args()

    files = glob.glob(args.src)
    if not files:
        raise SystemExit(f"No feature JSON files matched: {args.src}")

    os.makedirs(args.outdir, exist_ok=True)
    feats_path = os.path.join(args.outdir, "features.csv")
    meta_path  = os.path.join(args.outdir, "meta.json")

    fieldnames = ["ref_id","title","artist","bpm","loudness_lufs","energy","danceability","valence",
                "ttc_sec","runtime_sec","exposures","key","mode","rhythm_profile","genre","tags"]

    rows = []
    meta = {}
    for i, fp in enumerate(sorted(files), start=1):
        with open(fp, "r", encoding="utf-8") as f:
            j = json.load(f)

        feat = j.get("features", j)
        ref_id = f"{args.prefix}:{i:03d}"
        title = j.get("track_title") or j.get("title") or os.path.basename(fp)
        artist = j.get("artist") or ""

        nums = {
            "bpm": coerce_num(feat.get("bpm")),
            "duration_sec": coerce_num(feat.get("duration_sec")),
            "loudness_lufs": coerce_num(feat.get("loudness_lufs")),
            "energy": coerce_num(feat.get("energy")),
            "danceability": coerce_num(feat.get("danceability")),
            "valence": coerce_num(feat.get("valence")),
        }
        missing = [k for k, v in nums.items() if v is None]
        if missing:
            print(f"[warn] Skipping {fp} — missing required numerics: {missing}")
            continue

        ttc = coerce_num(j.get("ttc_sec")) or 0.0
        exp = coerce_num(j.get("exposures")) or 0.0

        key = feat.get("key") or j.get("key") or ""
        mode = feat.get("mode") or j.get("mode") or ""
        rhythm = feat.get("rhythm_profile") or ""
        genre = j.get("genre") or ""
        tags = feat.get("tags") or []
        tag_str = ",".join(tags) if isinstance(tags, list) else str(tags)

        rows.append({
            "ref_id": ref_id,
            "title": title,
            "artist": artist,
            "bpm": nums["bpm"],
            "loudness_lufs": nums["loudness_lufs"],
            "energy": nums["energy"],
            "danceability": nums["danceability"],
            "valence": nums["valence"],
            "ttc_sec": ttc,
            "runtime_sec": nums["duration_sec"],
            "exposures": exp,
            "key": key,
            "mode": mode,
            "rhythm_profile": rhythm,
            "genre": genre,
            "tags": tag_str
        })

        hci = j.get("HCI_v1")
        if isinstance(hci, str):
            try: hci = float(hci)
            except: hci = None
        hem = j.get("HEM") if isinstance(j.get("HEM"), dict) else None
        meta[ref_id] = {
            "HCI_v1": float(hci) if isinstance(hci, (int, float)) else 0.68,
            "HEM": hem if hem else {"Midtempo-Pop-Anthm": 0.5}
        }

    if not rows:
        raise SystemExit("No valid rows to write (all inputs skipped).")

    with open(feats_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {feats_path}")
    print(f"Wrote: {meta_path}")

if __name__ == "__main__":
    main()
