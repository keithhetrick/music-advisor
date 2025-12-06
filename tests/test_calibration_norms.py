import json
from pathlib import Path


CALIB_DIR = Path(__file__).resolve().parents[1] / "shared" / "calibration"


def test_market_norms_shape_and_ranges():
    data = json.loads((CALIB_DIR / "market_norms_us_pop.json").read_text())
    norms = data["MARKET_NORMS"]

    # Numeric fields present
    for key in [
        "tempo_bpm_mean",
        "tempo_bpm_std",
        "runtime_sec_mean",
        "runtime_sec_std",
        "loudness_mean",
        "loudness_std",
    ]:
        assert isinstance(norms[key], (int, float))

    # Key histogram is roughly normalized
    key_dist = norms["key_distribution"]
    assert isinstance(key_dist, dict) and key_dist, "key_distribution missing"
    assert abs(sum(key_dist.values()) - 1.0) < 0.05

    # Mode ratio totals to ~1.0 and has both modes
    mode_ratio = norms["mode_ratio"]
    assert set(mode_ratio) == {"major", "minor"}
    total_mode = mode_ratio["major"] + mode_ratio["minor"]
    assert 0.9 < total_mode < 1.1


def test_loudness_norms_metadata_consistent():
    data = json.loads((CALIB_DIR / "loudness_norms_us_pop_v1.json").read_text())

    assert data["version"].startswith("us_pop_loudness_")
    assert "capture_profile" in data and "reference_sample" in data

    capture = data["capture_profile"]
    assert capture["id"]
    assert isinstance(capture["known_offset_vs_spotify_db"], (int, float))

    market = data["market_norms_for_axes"]
    assert isinstance(market["loudness_mean_lufs"], (int, float))
    assert isinstance(market["loudness_std_lufs"], (int, float))
    # Guidance text remains present for future recalibration
    assert "intended_use" in market and "future_notes" in market
