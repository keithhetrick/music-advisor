#!/usr/bin/env python3
import json, hashlib, sys, zipfile, io

def sha256_bytes(b):
    import hashlib
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_zip.py MusicAdvisor_v2.6.0.zip")
        sys.exit(2)

    zip_path = sys.argv[1]
    with zipfile.ZipFile(zip_path, "r") as z:
        zip_names = set([n for n in z.namelist() if not n.endswith("/")])

        # Load manifest from inside ZIP
        manifest_name = "MusicAdvisor/Manifest/MANIFEST_v2.6.0.json"
        if manifest_name not in zip_names:
            print("ERROR: Manifest not found in ZIP:", manifest_name)
            sys.exit(1)

        manifest = json.loads(z.read(manifest_name).decode("utf-8"))
        expected = { "MusicAdvisor/" + f["path"]: f for f in manifest["files"] }

        # Check missing
        missing = [p for p in expected.keys() if p not in zip_names]
        # Check sha mismatches
        mismatched = []
        for path, meta in expected.items():
            if path in zip_names and meta.get("sha256"):
                data = z.read(path)
                sh = sha256_bytes(data)
                if sh != meta["sha256"]:
                    mismatched.append((path, meta["sha256"], sh))

        # Extra files (allow manifest + docs not listed)
        extras = sorted([n for n in zip_names if n.startswith("MusicAdvisor/") and n not in expected])

        # Report
        ok = True
        if missing:
            ok = False
            print("MISSING files:")
            for m in missing: print(" -", m)
        if mismatched:
            ok = False
            print("CHECKSUM MISMATCH:")
            for p, exp, got in mismatched:
                print(f" - {p}\n   expected: {exp}\n   got     : {got}")
        # Print extras as info (not fatal)
        if extras:
            print("EXTRA files (info):")
            for e in extras: print(" -", e)

        print("\nRESULT:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
