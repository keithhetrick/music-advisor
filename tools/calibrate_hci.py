#!/usr/bin/env python3
"""Compatibility shim: routes to tools/calibration/calibrate_hci.py"""
def apply_calibration_to_raw(raw: float, calibration: dict) -> float:
    """
    Apply linear calibration using dict with cap_min/cap_max and anchors (scale/offset).
    Expects calibration like shared/calibration/hci_calibration_pop_us_2025Q4.json.
    """
    cap_min = calibration.get("cap_min", 0.0)
    cap_max = calibration.get("cap_max", 1.0)
    anchor = calibration.get("anchors", {}).get("00_core_modern", {})
    scale = anchor.get("scale", 1.0)
    offset = anchor.get("offset", 0.0)
    val = raw * scale + offset
    if val < cap_min:
        val = cap_min
    if val > cap_max:
        val = cap_max
    return float(val)


def load_calibration(path) -> dict:
    from tools.calibration import calibrate_hci as calib_mod
    return calib_mod.load_calibration(path)


def main():
    from tools.calibration.calibrate_hci import main as _main
    _main()


if __name__ == "__main__":
    raise SystemExit(main())
