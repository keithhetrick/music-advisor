from pathlib import Path
import yaml
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def test_hitcheck_config_exists_and_has_keys():
    cfg_path = ROOT / "HitCheck" / "hitcheck" / "config.yaml"
    assert cfg_path.exists(), "HitCheck config.yaml missing"
    data = yaml.safe_load(cfg_path.read_text())
    assert data.get("paths") is not None
    assert data.get("defaults") is not None
    assert data.get("projection") is not None

    # Synthetic cohort shipped for smoke
    idx = ROOT / data["paths"]["index_npz"]
    feats = ROOT / data["paths"]["reference_features"]
    meta = ROOT / data["paths"]["reference_meta"]
    assert idx.exists(), "hitcheck_index.npz missing"
    assert feats.exists(), "reference features missing"
    assert meta.exists(), "reference meta missing"

    arr = np.load(idx)
    assert "X_ref" in arr and "meta" in arr
