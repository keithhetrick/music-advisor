#!/usr/bin/env python3
"""
Fit a monotonic (isotonic-like) mapping from HCI_v1(raw) -> calibrated_HCI,
using anchor folders as weak supervision (target anchors).

- Scans **_packs** under --packs-root for *.pack.json
- Infers anchor name from relative path (the folder containing _packs).
- Assigns a target score per anchor (configurable default below).
- Fits a monotone piecewise-linear map via PAV algorithm.
- Writes a JSON config consumed by pack_writer when CALIBRATION_CONFIG is set.

Usage:
  python calibration_fit.py \
    --packs-root "/.../audio_norm" \
    --out "/path/to/hci_calibration_pop_us_2025Q4.json"

Optional:
  --targets-json path/to/anchor_targets.json   # {"00_core_modern":0.85, ...}
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

DEFAULT_TARGETS = {
    "00_core_modern":             0.85,
    "01_echo_1985_89":            0.75,
    "02_echo_1990_94":            0.75,
    "03_echo_1995_99":            0.73,
    "04_echo_2000_04":            0.72,
    "05_echo_2005_09":            0.72,
    "06_echo_2010_14":            0.76,
    "07_echo_2015_19":            0.78,
    "08_indie_singer_songwriter": 0.55,
    "09_latin_crossover_eval":    0.75,
    "10_negatives_main_eval":     0.25,
    "11_negatives_canonical_eval":0.25,
    "12_negatives_novelty_eval":  0.20,
    "99_legacy_pop_eval":         0.55,
}

def pav_isotonic(x, y):
    """Pool Adjacent Violators algorithm to fit isotonic regression.
    Returns (xs, ys) piecewise-constant fit; we’ll convert to piecewise-linear."""
    # sort by x
    pts = sorted(zip(x, y), key=lambda t: t[0])
    xs, ys = [], []
    for xi, yi in pts:
        xs.append(xi); ys.append(yi)
        # merge backward while violating monotonicity
        while len(ys) >= 2 and ys[-2] > ys[-1]:
            # pool last two
            y_pool = (ys[-2] + ys[-1]) / 2.0
            x_pool = (xs[-2] + xs[-1]) / 2.0
            xs[-2:] = [x_pool]
            ys[-2:] = [y_pool]
    return xs, ys

def piecewise_linear_nodes(xs, ys):
    """Convert piecewise-constant PAV output into nodes for linear interpolation."""
    # De-duplicate by x and enforce [0,1] bounds
    nodes = []
    for x, y in zip(xs, ys):
        x = max(0.0, min(1.0, float(x)))
        y = max(0.0, min(1.0, float(y)))
        if not nodes or abs(nodes[-1][0] - x) > 1e-9:
            nodes.append((x, y))
        else:
            # average y if same x
            px, py = nodes[-1]
            nodes[-1] = (px, (py + y) / 2.0)
    # Ensure endpoints at 0 and 1
    if nodes[0][0] > 0.0:
        nodes.insert(0, (0.0, nodes[0][1]))
    if nodes[-1][0] < 1.0:
        nodes.append((1.0, nodes[-1][1]))
    return nodes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True, help="Root containing per-anchor _packs with *.pack.json")
    ap.add_argument("--out", required=True, help="Output JSON config path")
    ap.add_argument("--targets-json", default=None, help="Optional JSON mapping anchor->target score")
    args = ap.parse_args()

    packs_root = Path(args.packs_root).expanduser().resolve()
    if not packs_root.is_dir():
        print(f"[fit] not a dir: {packs_root}", file=sys.stderr); sys.exit(2)

    targets = DEFAULT_TARGETS.copy()
    if args.targets_json:
        with open(args.targets_json, "r") as f:
            targets.update(json.load(f))

    # Gather raw points
    xs, ys = [], []
    count = 0
    for pack in packs_root.rglob("**/_packs/**/*.pack.json"):
        # anchor is the folder containing _packs, i.e., pack.parents until you find "_packs"
        parts = list(pack.parts)
        if "_packs" not in parts:
            continue
        idx = parts.index("_packs")
        if idx == 0:
            continue
        anchor = parts[idx-1]
        if anchor not in targets:
            continue
        try:
            d = json.loads(pack.read_text())
            hci = float(d.get("HCI_v1",{}).get("HCI_v1_score"))
        except Exception:
            continue
        xs.append(max(0.0, min(1.0, hci)))
        ys.append(targets[anchor])
        count += 1

    if count < 10:
        print(f"[fit] insufficient packs found under {packs_root} (found={count})", file=sys.stderr)
        sys.exit(2)

    # Fit isotonic (monotone increasing) mapping
    pav_x, pav_y = pav_isotonic(xs, ys)
    nodes = piecewise_linear_nodes(pav_x, pav_y)

    out = {
        "version": "hci_calibration.v1",
        "created_at": int(time.time()),
        "source": str(packs_root),
        "supervision": "anchor_targets",
        "targets": targets,
        "mapping": {
            "type": "piecewise_linear",
            "nodes": [{"x": x, "y": y} for x, y in nodes],
            "clip": True
        }
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"[fit] wrote {args.out}  (nodes={len(nodes)})")

if __name__ == "__main__":
    main()
