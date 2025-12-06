#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def load_json(path: Path):
    return json.loads(path.read_text())

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True))

def main():
    parser = argparse.ArgumentParser(
        description="Apply HCI_v1 policy (anchors vs WIP, WIP ceiling) to .hci.json files."
    )
    parser.add_argument("--root", required=True,
                        help="Root directory containing *.hci.json files.")
    parser.add_argument("--calib-index", required=True,
                        help="Path to calibration_index_2025Q4.json (defines anchor slugs).")
    parser.add_argument("--policy", required=True,
                        help="Path to hci_policy_v1.json (defines WIP ceiling, etc.).")
    args = parser.parse_args()

    root = Path(args.root)
    calib_index = load_json(Path(args.calib_index))
    policy = load_json(Path(args.policy))

    calib_slugs = set(calib_index.get("slugs", []))
    wip_max = float(policy.get("wip_max_score", 0.93))
    policy_name = policy.get("name", "HCI_v1_policy")
    policy_version = policy.get("version", "1.0")

    print(f"[INFO] Loaded {len(calib_slugs)} calibration slugs from {args.calib_index}")
    print(f"[INFO] WIP max score = {wip_max:.3f}")

    count_total = 0
    count_anchors = 0
    count_wip = 0

    for hci_path in root.rglob("*.hci.json"):
        count_total += 1
        data = load_json(hci_path)

        slug = hci_path.parent.name  # folder name = slug
        is_anchor = slug in calib_slugs

        raw = data.get("HCI_v1_score_raw")
        score = data.get("HCI_v1_score")

        # If this HCI file is still legacy-format or missing fields, skip gently.
        if raw is None or score is None:
            continue

        role = "anchor" if is_anchor else "wip"

        # Keep a pre-policy copy for transparency
        pre_policy = float(score)
        adj = float(score)

        if not is_anchor:
            # WIP songs are softly capped; they cannot occupy the full 1.0 band.
            if adj > wip_max:
                adj = wip_max

        # Round to 3 decimals for consistency with the rest of the pipeline
        adj = round(adj, 3)
        pre_policy = round(pre_policy, 3)

        # Write back
        data["HCI_v1_role"] = role
        data["HCI_v1_score_pre_policy"] = pre_policy
        data["HCI_v1_score"] = adj

        meta = data.get("meta", {})
        policy_meta = {
            "name": policy_name,
            "version": policy_version,
            "wip_max_score": wip_max
        }
        meta["policy"] = policy_meta
        data["meta"] = meta

        save_json(hci_path, data)

        if is_anchor:
            count_anchors += 1
        else:
            count_wip += 1

    print(f"[OK] Processed {count_total} .hci.json files under {root}")
    print(f"     anchors: {count_anchors}, wip: {count_wip}")
    print(f"[NOTE] For every file, HCI_v1_score_pre_policy is preserved for audit; "
          f"HCI_v1_score is the post-policy, user-facing score.")

if __name__ == "__main__":
    main()
