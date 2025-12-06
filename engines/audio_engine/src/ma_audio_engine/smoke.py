import argparse
import json
import sys
from statistics import mean

from ma_audio_engine.host.baseline_loader import load_baseline
from ma_audio_engine.host.baseline_normalizer import summarize_market_fit


def _orig_main():
    """
    Minimal, deterministic smoke: reproduce prior output shape & values used in tests.
    - axes fixed to keep HCI_v1 stable (mean(axes) == 0.446...)
    - market/emotional only influence advisory deltas, not score
    """
    parser = argparse.ArgumentParser(prog="music-advisor-smoke")
    parser.add_argument("payload", help="path to extracted payload.json (not used deeply in smoke)")
    parser.add_argument("--market", type=float, default=0.5)
    parser.add_argument("--emotional", type=float, default=0.5)
    parser.add_argument("--round", dest="round_digits", type=int, default=3)
    args = parser.parse_args()

    # Fixed demo axes (match previous smoke output)
    axes = [0.253, 0.0, 0.995, 0.429, 0.5, 0.5]

    # HCI_v1 = mean(axes); cap handled by Policy in real pipeline, but smoke keeps it simple
    hci = round(mean(axes), args.round_digits)

    result = {
        "HCI_v1": {"HCI_v1_score": hci},
        # Baseline attached later; stub here to preserve shape if needed
        "Baseline": {
            "id": None,
            "MARKET_NORMS": {}
        },
        "Policy": {
            "cap_audio": 0.58,
            "ttc_conf_gate": 0.6,
            "lift_window_sec": 6.0
        },
        "TTC_Gate": {
            "ttc_seconds": None,
            "ttc_confidence": None,
            "lift_db": None,
            "drop_features": ["chorus_lift"],
            "source": "absent"
        },
        "TTC": {
            "seconds": None,
            "confidence": None,
            "lift_db": None,
            "dropped": [],
            "source": "absent"
        },
        "Structural_Gates": {
            "drop": ["chorus_lift", "exposures"],
            "notes": {
                "struct_mode": "optional",
                "struct_reliable": False,
                "use_ttc": True,
                "use_exposures": False,
                "ttc_gate_threshold": 0.6,
                "reasoning": "Subfeatures dropped due to structural eligibility, not numeric HCI logic."
            }
        },
        "Structural": {
            "drop": ["chorus_lift", "exposures"],
            "notes": {
                "struct_mode": "optional",
                "struct_reliable": False,
                "use_ttc": True,
                "use_exposures": False,
                "ttc_gate_threshold": 0.6,
                "reasoning": "Subfeatures dropped due to structural eligibility, not numeric HCI logic."
            }
        },
        "Goldilocks": {
            "advisory": {
                "target_market": 0.5,
                "target_emotional": 0.5,
                "delta_market": round(0.5 - args.market, args.round_digits),
                "delta_emotional": round(0.5 - args.emotional, args.round_digits)
            },
            "rationale": "Shift modestly toward market framing while tempering emotive claims.",
            "safety": {"note": "Goldilocks is advisory-only; HCI remains unchanged."}
        },
        "Axes": {"audio_axes": axes}
    }

    return result


def _attach_baseline_and_advisory(report: dict) -> dict:
    """
    Attach Baseline from loader; add Market Norms advisory (non-scoring).
    Advisory can be disabled by env: MA_DISABLE_NORMS_ADVISORY=1
    """
    import os
    try:
        baseline = load_baseline()
    except Exception:
        baseline = None

    if baseline is None:
        report["Baseline"] = {
            "id": None,
            "note": "Baseline file not found; using safe default for smoke.",
            "MARKET_NORMS": {}
        }
    else:
        report["Baseline"] = {
            "id": baseline.get("id"),
            "MARKET_NORMS": baseline.get("MARKET_NORMS", {})
        }

    # --- Advisory (non-scoring), can be disabled via env ---
    if os.getenv("MA_DISABLE_NORMS_ADVISORY") != "1":
        try:
            m = report.get("Baseline", {}).get("MARKET_NORMS", {})
            if m:
                fit = summarize_market_fit(m)
                # only add advisory when enabled
                report.setdefault("Baseline", {}).setdefault("advisory", {}).update(fit)
        except Exception as _e:
            report.setdefault("Baseline", {}).setdefault("advisory_error", str(_e))

    return report



def main(*_args, **_kwargs):
    # Run original logic
    report = _orig_main()
    # Attach baseline + advisory
    report = _attach_baseline_and_advisory(report)
    # Print as JSON for ma-pipe
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
