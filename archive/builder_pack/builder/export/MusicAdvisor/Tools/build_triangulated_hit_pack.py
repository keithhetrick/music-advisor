#!/usr/bin/env python3
# build_triangulated_hit_pack.py — create a balanced hit reference JSON
import json, argparse, datetime, pathlib

def mk_track(title, artist, url=None, notes=None):
    t = {"title": title, "artist": artist}
    if url: t["url"] = url
    if notes: t["notes"] = notes
    return t

def main():
    ap = argparse.ArgumentParser(description="Build a triangulated hit pack for Trend Snapshot")
    ap.add_argument("--tag", required=True, help="e.g., HitPulse_2025_11_A")
    # Pillar A: Narrative truth (folk sincerity)
    ap.add_argument("--a-title", required=True)
    ap.add_argument("--a-artist", required=True)
    ap.add_argument("--a-url", default=None)
    ap.add_argument("--a-notes", default="folk-pop,narrative truth,acoustic-forward")
    # Pillar B: Emotional power (soul/gospel/anthem)
    ap.add_argument("--b-title", required=True)
    ap.add_argument("--b-artist", required=True)
    ap.add_argument("--b-url", default=None)
    ap.add_argument("--b-notes", default="soul-pop,emotional belt,gospel warmth")
    # Pillar C: Modern lift (contemporary pop edge)
    ap.add_argument("--c-title", required=True)
    ap.add_argument("--c-artist", required=True)
    ap.add_argument("--c-url", default=None)
    ap.add_argument("--c-notes", default="modern pop,dramatic lift,format fit")
    ap.add_argument("-o","--out", default=None)
    args = ap.parse_args()

    def split_notes(s): return [x.strip() for x in s.split(",") if x.strip()]

    payload = {
        "source": "spotify",
        "playlist": args.tag,
        "generated_at": datetime.date.today().isoformat(),
        "tracks": [
            mk_track(args.a_title, args.a_artist, args.a_url, split_notes(args.a_notes)),
            mk_track(args.b_title, args.b_artist, args.b_url, split_notes(args.b_notes)),
            mk_track(args.c_title, args.c_artist, args.c_url, split_notes(args.c_notes)),
        ]
    }

    out = pathlib.Path(args.out or f"./imports/{args.tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Wrote {out}")

if __name__ == "__main__":
    main()
