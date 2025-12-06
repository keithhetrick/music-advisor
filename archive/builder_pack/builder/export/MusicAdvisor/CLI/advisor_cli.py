# MusicAdvisor/CLI/advisor_cli.py

from __future__ import annotations
import json
import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# --- Ensure repo root is importable when running this file directly ---
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --- Policy parser (prefer real; fallback inline) ---
try:
    from MusicAdvisor.Core.policy import parse_policy  # capitalized legacy shim
except Exception:
    import re
    def parse_policy(txt: str):
        t = txt or ""
        sp = {
            "mode": ("strict" if "mode=strict" in t.lower()
                     else ("optional" if "mode=optional" in t.lower() else None)),
            "reliable": "reliable=true" in t.lower(),
            "use_ttc": "use_ttc=true" in t.lower(),
            "use_exposures": "use_exposures=true" in t.lower(),
        }
        pri_m = re.search(r"priors\s*=\s*\{([^}]+)\}", t, re.IGNORECASE)
        cap_m = re.search(r"caps\s*=\s*\{([^}]+)\}", t, re.IGNORECASE)
        gp = {
            "active": "GOLDILOCKS_POLICY: active=true" in t,
            "priors_raw": pri_m.group(1) if pri_m else None,
            "caps_raw": cap_m.group(1) if cap_m else None,
        }
        return {"STRUCTURE_POLICY": sp, "GOLDILOCKS_POLICY": gp}

# --- Ingest (calls ingest_normalizer internally) ---
from MusicAdvisor.Core.ingest_pipeline import ingest

# --- Scorer optional: try to import; fallback if missing ---
HAS_ENGINE = False
_run_hci = None
try:
    from MusicAdvisor.Core.engine import run_hci as _run_hci
    HAS_ENGINE = True
except Exception:
    HAS_ENGINE = False

# --- End-to-end extractor-style pipeline (tolerant import) ---
try:
    from Pipeline.end_to_end import score_from_extractor_payload
except Exception:
    try:
        from MusicAdvisor.Pipeline.end_to_end import score_from_extractor_payload  # type: ignore
    except Exception:
        score_from_extractor_payload = None  # type: ignore

# --- Host policy (tolerant import: lowercase then legacy path) ---
try:
    from music_advisor.host.policy import Policy as HostPolicy
except Exception:
    try:
        from MusicAdvisor.music_advisor.host.policy import Policy as HostPolicy  # type: ignore
    except Exception:
        HostPolicy = None  # type: ignore


def _auto_client_for_pack(pack_path: str) -> str | None:
    """Find a helper file next to the pack; prefer *.client.rich.txt then *.client*.txt."""
    d = Path(pack_path).parent
    rich = sorted(d.glob("*.client.rich.txt"))
    if rich:
        return str(rich[0])
    plain = sorted(d.glob("*.client*.txt"))
    return str(plain[0]) if plain else None


# ===== Path: --pack/--client (client-only helper) =====
def _run_from_pack(args: argparse.Namespace) -> Dict[str, Any]:
    # Resolve helper path (client only)
    helper_arg = args.client
    helper_path = Path(helper_arg)
    if helper_arg.upper() == "AUTO" or helper_path.is_dir():
        auto = _auto_client_for_pack(args.pack)
        if not auto:
            raise SystemExit("[advisor] ERROR: Could not auto-find a *client*.txt next to the pack.")
        helper_path = Path(auto)

    if not helper_path.exists():
        raise SystemExit(f"[advisor] ERROR: helper file not found: {helper_path}")
    if not Path(args.pack).exists():
        raise SystemExit(f"[advisor] ERROR: pack file not found: {args.pack}")

    # Load helper contents + staged packs
    helper_txt = helper_path.read_text(encoding="utf-8", errors="ignore")
    staged = ingest(args.pack, helper_txt)

    payload: Dict[str, Any] = {
        "policy_snapshot": parse_policy(helper_txt),
        "staged": staged
    }

    # Attempt HCI — always emit an HCI_v1 block.
    hci_block: Dict[str, Any]
    if HAS_ENGINE and callable(_run_hci):
        try:
            result = _run_hci(staged)
            if isinstance(result, dict) and "HCI_v1" in result:
                hci_block = result["HCI_v1"]
            elif isinstance(result, dict) and "HCI_v1_score" in result:
                hci_block = result
            else:
                hci_block = {"HCI_v1_score": result}  # possibly a float
        except Exception as e:
            hci_block = {"error": f"HCI engine failed: {e}"}
    else:
        hci_block = {"error": "HCI engine unavailable; install/enable engine to compute numeric score."}

    # Optional rounding
    rd = getattr(args, "round_digits", None)
    if rd is not None and isinstance(hci_block, dict) and "HCI_v1_score" in hci_block and isinstance(hci_block["HCI_v1_score"], (int, float)):
        hci_block["HCI_v1_score"] = round(float(hci_block["HCI_v1_score"]), int(rd))

    payload["HCI_v1"] = hci_block
    return payload


# ===== New subcommand: from-json (extractor-style) ============================
def _run_from_json(args: argparse.Namespace) -> Dict[str, Any]:
    if score_from_extractor_payload is None or HostPolicy is None:
        raise SystemExit("from-json is unavailable: missing Pipeline.end_to_end or Host Policy import.")

    payload_path = Path(args.payload_json)
    if not payload_path.exists():
        raise SystemExit(f"ERROR: payload json not found: {payload_path}")
    raw = json.loads(payload_path.read_text())

    pol = HostPolicy()
    if args.cap is not None:
        pol.cap_audio = float(args.cap)
    if args.gate is not None:
        pol.ttc_conf_gate = float(args.gate)
    if args.lift is not None:
        pol.lift_window_sec = float(args.lift)

    out = score_from_extractor_payload(
        raw=raw,
        host_policy=pol,
        observed_market=args.market,
        observed_emotional=args.emotional,
    )

    # Optional rounding
    rd = getattr(args, "round_digits", None)
    if rd is not None and isinstance(out, dict):
        hci = out.get("HCI_v1", {})
        if isinstance(hci, dict) and "HCI_v1_score" in hci and isinstance(hci["HCI_v1_score"], (int, float)):
            hci["HCI_v1_score"] = round(float(hci["HCI_v1_score"]), int(rd))
            out["HCI_v1"] = hci

    return out


# ===== Argument parsing =======================================================
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MusicAdvisor CLI (packs & extractor JSON). Always emits HCI_v1.")
    sub = p.add_subparsers(dest="cmd")

    # from-pack
    sp_pack = sub.add_parser("from-pack", help="Ingest a pack + client helper; run HCI if engine present, else provide HCI_v1 error.")
    sp_pack.add_argument("--pack", required=True, help="Path to pack JSON")
    sp_pack.add_argument("--client", required=True, help="Path to client.txt or client.rich.txt (or a dir containing it, or the literal 'AUTO')")
    sp_pack.add_argument("--round", dest="round_digits", type=int, default=None, help="Round HCI_v1 to N decimals")
    sp_pack.add_argument("--export", help="Write full JSON to this path")
    sp_pack.add_argument("--print-audit", dest="print_audit", action="store_true", help="Also print to stdout")

    # from-json
    sp_json = sub.add_parser("from-json", help="Run end-to-end scoring from an extractor-style JSON payload.")
    sp_json.add_argument("payload_json", help="Path to extractor JSON (axes[6], TTC hints, spans, sr, etc.)")
    sp_json.add_argument("--market", type=float, default=0.50, help="Observed market (0..1) for Goldilocks advisory")
    sp_json.add_argument("--emotional", type=float, default=0.50, help="Observed emotional (0..1) for Goldilocks")
    sp_json.add_argument("--gate", type=float, default=None, help="Override TTC confidence gate (default Policy)")
    sp_json.add_argument("--cap", type=float, default=None, help="Override audio cap (default Policy)")
    sp_json.add_argument("--lift", type=float, default=None, help="Override lift window sec (default Policy)")
    sp_json.add_argument("--round", dest="round_digits", type=int, default=None, help="Round HCI_v1 to N decimals")
    sp_json.add_argument("--export", help="Write full JSON to this path")
    sp_json.add_argument("--print-audit", dest="print_audit", action="store_true", help="Also print to stdout")

    # Legacy passthrough (no subcommand) – suppressed
    p.add_argument("--pack", help=argparse.SUPPRESS)
    p.add_argument("--client", help=argparse.SUPPRESS)
    p.add_argument("--export", help=argparse.SUPPRESS)
    p.add_argument("--print-audit", dest="print_audit", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--round", dest="round_digits", type=int, default=None, help=argparse.SUPPRESS)

    return p


# ===== Main ==================================================================
def main():
    p = _build_parser()
    args = p.parse_args()

    if args.cmd == "from-pack":
        payload = _run_from_pack(args)
    elif args.cmd == "from-json":
        payload = _run_from_json(args)
    else:
        # Legacy path: treat as from-pack if flags exist
        if args.pack and getattr(args, "client", None):
            # Fabricate a minimal Namespace for legacy
            class _A: pass
            legacy = _A()
            legacy.pack = args.pack
            legacy.client = getattr(args, "client", None)
            legacy.export = getattr(args, "export", None)
            legacy.print_audit = getattr(args, "print_audit", False)
            legacy.round_digits = getattr(args, "round_digits", None)
            payload = _run_from_pack(legacy)
        else:
            p.print_help()
            raise SystemExit(2)

    out = json.dumps(payload, indent=2)
    export_path = getattr(args, "export", None)
    if export_path:
        Path(export_path).write_text(out, encoding="utf-8")
    if getattr(args, "print_audit", False) or not export_path:
        print(out)


if __name__ == "__main__":
    main()
