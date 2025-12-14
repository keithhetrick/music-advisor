from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_core_calibration_files_present():
    required = [
        "shared/calibration/hci_calibration_pop_us_2025Q4.json",
        "shared/calibration/hci_policy_v1.json",
        "shared/calibration/lci_norms_us_pop_v1.json",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Missing calibration files: {missing}"
