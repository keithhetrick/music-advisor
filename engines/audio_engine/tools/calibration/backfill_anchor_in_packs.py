#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

def infer_anchor_from_path(pack_path: Path) -> str:
    parts = pack_path.parts
    try:
        idx = parts.index("audio_norm")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    except ValueError:
        pass
    return "UNKNOWN"

def main():
    if len(sys.argv) < 2:
        print("Usage: backfill_anchor_in_packs.py <packs-root>", file=sys.stderr)
        sys.exit(2)

    root = Path(sys.argv[1])
    changed = 0
    for p in root.rglob("**/_packs/**/*.pack.json"):
        try:
            d = json.loads(p.read_text())
            anchor = d.get("anchor")
            if not anchor or anchor == "UNKNOWN":
                a = infer_anchor_from_path(p)
                if a and a != "UNKNOWN":
                    d["anchor"] = a
                    tmp = str(p) + ".tmp"
                    with open(tmp, "w") as f:
                        json.dump(d, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, p)
                    changed += 1
        except Exception as e:
            print(f"[anchor] skip {p}: {e}", file=sys.stderr)
    print(f"[anchor] updated packs: {changed}")

if __name__ == "__main__":
    main()
