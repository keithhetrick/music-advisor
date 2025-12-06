#!/usr/bin/env python3
# tools/freeze_pack.py
import argparse, json, hashlib, os, sys, time
from pathlib import Path

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Freeze a PACK snapshot with hashes and env info.")
    ap.add_argument("--pack", required=True, help="path to pack.json")
    ap.add_argument("--audio", required=False, help="optional path to source audio for hashing")
    ap.add_argument("--out-dir", default="datahub/packs/snapshots", help="snapshot dir")
    args = ap.parse_args()

    pack_path = Path(args.pack).expanduser().resolve()
    if not pack_path.exists():
        print(f"[freeze_pack] missing pack: {pack_path}", file=sys.stderr); sys.exit(2)

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = json.loads(pack_path.read_text())
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = pack.get("Audio", {}).get("audio_name") or pack_path.stem
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)
    snap_name = f"{safe}_{ts}.pack.snapshot.json"
    snap_path = out_dir / snap_name

    env = {
        "python": sys.version.split()[0],
        "librosa": _safe_ver("librosa"),
        "numpy": _safe_ver("numpy"),
        "scipy": _safe_ver("scipy"),
        "sklearn": _safe_ver("sklearn"),
    }
    audio_hash = None
    if args.audio:
        apath = Path(args.audio).expanduser()
        if apath.exists():
            audio_hash = sha256_path(apath)

    snap = {
        "snapshot": {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pack_file": str(pack_path),
            "pack_sha256": sha256_path(pack_path),
            "audio_file": str(Path(args.audio).resolve()) if args.audio else None,
            "audio_sha256": audio_hash,
            "baseline_id": (pack.get("Baseline") or {}).get("id"),
            "policy": pack.get("Policy"),
            "env": env,
        },
        "pack": pack,
    }
    snap_path.write_text(json.dumps(snap, indent=2, ensure_ascii=False))
    print(f"[freeze_pack] wrote {snap_path}")

def _safe_ver(mod):
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "unknown")
    except Exception:
        return "missing"

if __name__ == "__main__":
    main()
