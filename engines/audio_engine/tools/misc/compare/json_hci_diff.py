#!/usr/bin/env python3
"""
json_hci_diff.py — canonical compare for MusicAdvisor HCI outputs

Compares two JSON exports (builder vs local engine) and reports:
- exact equality of canonicalized structures, with float tolerance
- per-path diffs (what changed, where)
- exit code 0 if equivalent, 1 if different, 2 on error

Normalization:
- sort dict keys
- remove/ignore volatile fields (timestamps, absolute file paths)
- optional path-based ignores (see IGNORE_PATHS)
"""

import sys, json, math
from pathlib import Path

# tweak as needed
FLOAT_EPS = 1e-6
IGNORE_KEYS = {
    # common volatile keys:
    "generated_at", "effective_utc", "created_at", "updated_at",
    "runtime_ms", "build_id", "commit", "hostname", "machine",
    # file-specific:
    "pack_path", "sibling_sources",
}
# optional full JSON-path ignores (dot-notation)
IGNORE_PATHS = {
    # examples:
    # "Baseline.note",
    # "Advisor.meta.session_id"
}

def load_json(path):
    txt = Path(path).read_text(encoding="utf-8", errors="ignore")
    try:
        return json.loads(txt)
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {path} ({e})", file=sys.stderr)
        sys.exit(2)

def should_ignore_key(key):
    return key in IGNORE_KEYS

def should_ignore_path(path):
    # path like "HCI_v1.Historical" etc.
    return path in IGNORE_PATHS

def canonicalize(obj):
    # remove volatile keys, normalize types (no special date handling needed)
    if isinstance(obj, dict):
        out = {}
        for k in sorted(obj.keys()):
            if should_ignore_key(k):
                continue
            out[k] = canonicalize(obj[k])
        return out
    elif isinstance(obj, list):
        return [canonicalize(x) for x in obj]
    else:
        return obj

def is_float(x):
    return isinstance(x, float) or isinstance(x, int)  # treat ints as floats for tolerance

def eq(a, b):
    # equality with float tolerance
    if is_float(a) and is_float(b):
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=FLOAT_EPS)
    return a == b

def diff(a, b, path=""):
    """
    Returns list of (path, left, right) differences.
    """
    diffs = []
    if type(a) != type(b):
        diffs.append((path or "$", a, b))
        return diffs

    if isinstance(a, dict):
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            p = f"{path}.{k}" if path else k
            if should_ignore_path(p):
                continue
            if k not in a:
                diffs.append((p, "<missing>", b[k] ))
            elif k not in b:
                diffs.append((p, a[k], "<missing>" ))
            else:
                diffs.extend(diff(a[k], b[k], p))
        return diffs

    if isinstance(a, list):
        if len(a) != len(b):
            diffs.append((path or "$", f"<len {len(a)}>", f"<len {len(b)}>"))
            # compare element-wise up to min length to be helpful
            n = min(len(a), len(b))
            for i in range(n):
                diffs.extend(diff(a[i], b[i], f"{path}[{i}]"))
            return diffs
        for i, (x, y) in enumerate(zip(a, b)):
            diffs.extend(diff(x, y, f"{path}[{i}]"))
        return diffs

    # scalars
    if not eq(a, b):
        diffs.append((path or "$", a, b))
    return diffs

def main():
    if len(sys.argv) != 3:
        print("Usage: json_hci_diff.py <builder_export.json> <local_export.json>", file=sys.stderr)
        sys.exit(2)

    left = canonicalize(load_json(sys.argv[1]))
    right = canonicalize(load_json(sys.argv[2]))

    # Optional: enforce presence of critical blocks before comparing
    # (uncomment if you want hard checks)
    # for p in ["HCI_v1", "Baseline", "policy_snapshot"]:
    #     if p not in left or p not in right:
    #         print(f"[WARN] Missing critical block '{p}' in one of the files.", file=sys.stderr)

    diffs = diff(left, right, "")
    if not diffs:
        print("✅ MATCH: canonical outputs are equivalent (within tolerance).")
        sys.exit(0)

    print("❌ DIFF: outputs differ. Showing first 50 differences:")
    for i, (p, a, b) in enumerate(diffs[:50], 1):
        print(f"{i:02d}. {p}: {a}  ≠  {b}")
    if len(diffs) > 50:
        print(f"... (+{len(diffs)-50} more)")

    # helpful summary for core HCI block if present
    try:
        lh = left.get("HCI_v1", {})
        rh = right.get("HCI_v1", {})
        if lh and rh:
            print("\nHCI_v1 summary (left vs right):")
            keys = ["HCI_v1_score","Historical","Cultural","Market","Emotional","Sonic","Creative"]
            for k in keys:
                if k in lh or k in rh:
                    print(f" - {k}: {lh.get(k)}  vs  {rh.get(k)}")
    except Exception:
        pass

    sys.exit(1)

if __name__ == "__main__":
    main()
