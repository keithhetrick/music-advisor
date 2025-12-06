# Calibration config helpers.
import pathlib
import yaml

from ma_config.paths import get_calibration_root


def _default_cfg() -> dict:
    calib_root = get_calibration_root() / "audio"
    fit_sets = [
        calib_root / "00_core_modern",
        calib_root / "01_echo_85_95",
        calib_root / "02_echo_00_10",
        calib_root / "03_echo_10_14",
        calib_root / "04_echo_15_19",
        calib_root / "05_echo_20_24",
    ]
    eval_sets = [
        calib_root / "10_golden_set",
        calib_root / "13_negatives_out_of_domain",
        calib_root / "14_negatives_novelty_eval",
        calib_root / "99_legacy_pop_eval",
    ]
    return {"fit_sets": [str(p) for p in fit_sets], "eval_sets": [str(p) for p in eval_sets]}


def load_config(path: str | None = None) -> dict:
    if path is None:
        return _default_cfg()
    p = pathlib.Path(path)
    if not p.exists():
        return _default_cfg()
    return yaml.safe_load(p.read_text())
