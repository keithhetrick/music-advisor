import sys
from pathlib import Path

import pytest

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.cache_utils import FeatureCache  # noqa: E402
from tools.ma_audio_features import select_tempo_with_folding  # noqa: E402


def test_feature_cache_hit_and_stale(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FeatureCache(cache_dir=str(cache_dir))

    source_hash = "abc123"
    cfg_fp = "config_fingerprint_example"
    source_mtime = 123.0
    payload = {"source_mtime": source_mtime, "foo": "bar"}

    # Store then load with matching mtime -> hit
    cache.store(source_hash=source_hash, config_fingerprint=cfg_fp, payload=payload)
    loaded = cache.load(source_hash=source_hash, config_fingerprint=cfg_fp, source_mtime=source_mtime)
    assert loaded is not None
    assert loaded["foo"] == "bar"

    # Changing mtime invalidates cache
    stale = cache.load(
        source_hash=source_hash,
        config_fingerprint=cfg_fp,
        source_mtime=source_mtime + 5.0,
    )
    assert stale is None

    # No temp files left behind
    tmp_files = list(cache_dir.glob("*.tmp"))
    assert not tmp_files


@pytest.mark.parametrize(
    "tempo,expected_primary,label",
    [
        (60.0, 120.0, "double_selected_folded_to_120.0_bpm"),  # chooses 2x because closer to 110
        (220.0, 110.0, "base_selected_folded_to_110.0_bpm"),   # folds down into comfort window
    ],
)
def test_tempo_folding_selection(tempo: float, expected_primary: float, label: str) -> None:
    primary, alt_half, alt_double, reason = select_tempo_with_folding(tempo)
    assert primary == pytest.approx(expected_primary)
    assert alt_half is not None
    assert alt_double is not None
    assert label in reason


def test_tempo_folding_none_input() -> None:
    primary, alt_half, alt_double, reason = select_tempo_with_folding(None)
    assert primary is None
    assert alt_half is None
    assert alt_double is None
    assert reason == "no_tempo"
