#!/usr/bin/env python3
import json, hashlib, os, sys, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # MusicAdvisor/
MANIFEST_PATH = os.path.join(ROOT, "Manifest", "MANIFEST_v2.6.0.json")

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["generated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    missing = []
    for entry in manifest["files"]:
        rel = entry["path"]
        abs_path = os.path.join(ROOT, rel)
        if not os.path.isfile(abs_path):
            missing.append(rel)
            entry["bytes"] = 0
            entry["sha256"] = ""
            continue
        entry["bytes"] = os.path.getsize(abs_path)
        entry["sha256"] = sha256_of(abs_path)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    if missing:
        print("WARNING: Missing files in manifest:")
        for m in missing: print(" -", m)
        sys.exit(1)
    else:
        print("Manifest updated:", MANIFEST_PATH)

if __name__ == "__main__":
    main()
