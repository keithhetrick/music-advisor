#!/usr/bin/env python3
import argparse, re, unicodedata
from pathlib import Path

AUDIO_EXTS = {".wav",".wave",".aiff",".aif",".flac",".mp3",".m4a",".aac",".ogg"}

def slugify(s: str) -> str:
    # fold unicode → ascii
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = s.lower()
    s = s.replace("&", " and ")
    # keep alnum, space, dash, underscore
    s = re.sub(r"[^a-z0-9\-_\. ]+", "", s)
    # spaces → underscore
    s = re.sub(r"\s+", "_", s)
    # collapse repeats
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"-+", "-", s)
    # trim underscores/dots from ends
    s = s.strip("._")
    return s

def sanitize_file(p: Path, dry_run=False):
    new_name = slugify(p.stem) + p.suffix.lower()
    if new_name == p.name:
        return None
    target = p.with_name(new_name)
    if dry_run:
        print(f"[dry] {p.name} -> {target.name}")
    else:
        p.rename(target)
        print(f"[ok]  {p.name} -> {target.name}")
    return target

def walk(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p

def main():
    ap = argparse.ArgumentParser(description="Sanitize audio filenames: spaces → underscores, ASCII-only, lowercase.")
    ap.add_argument("--root", required=True, help="Folder to sanitize (e.g., calibration/audio)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    for p in walk(root):
        sanitize_file(p, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
