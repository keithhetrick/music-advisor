from pathlib import Path

from ma_config.paths import (
    get_core_1600_csv_path,
    get_lyric_intel_db_path,
    get_historical_echo_db_path,
    get_features_output_root,
    get_hot100_lyrics_audio_path,
    get_kaggle_year_end_lyrics_path,
    get_external_data_root,
)
from ma_config.constants import ERA_BUCKETS, ERA_BUCKET_MISC
from ma_config.profiles import DEFAULT_LCI_CALIBRATION_PATH
from ma_config.audio import (
    DEFAULT_HCI_CALIBRATION_PATH,
    DEFAULT_MARKET_NORMS_PATH,
    resolve_market_norms,
    resolve_hci_v2_targets,
    resolve_hci_v2_corpus,
    resolve_hci_v2_training_out,
)
from ma_lyrics_engine import lanes


def test_get_lyric_intel_db_path_respects_env(monkeypatch, tmp_path):
    custom_root = tmp_path / "rootdata"
    monkeypatch.setenv("MA_DATA_ROOT", str(custom_root))
    expected = custom_root / "private" / "local_assets" / "lyric_intel" / "lyric_intel.db"
    assert get_lyric_intel_db_path() == expected


def test_lanes_use_constants_for_buckets_and_tiers():
    assert lanes.era_bucket(1990) == "1985_1994"
    assert lanes.era_bucket(2026) == ERA_BUCKET_MISC
    assert lanes.tier_from_rank(40) == 1
    assert lanes.tier_from_rank(150) == 3
    assert lanes.tier_from_rank(250) is None


def test_default_lci_calibration_path_exists():
    assert DEFAULT_LCI_CALIBRATION_PATH.name == "lci_calibration_us_pop_v1.json"
    assert DEFAULT_LCI_CALIBRATION_PATH.exists()


def test_audio_defaults_exist_and_env_override(monkeypatch, tmp_path):
    assert DEFAULT_HCI_CALIBRATION_PATH.exists()
    assert DEFAULT_MARKET_NORMS_PATH.exists()

    custom_norms = tmp_path / "norms.json"
    custom_norms.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("AUDIO_MARKET_NORMS", str(custom_norms))
    path, cfg = resolve_market_norms(None, log=lambda *_args, **_kwargs: None)
    assert path == custom_norms
    assert cfg == {}


def test_historical_echo_db_path_env(monkeypatch, tmp_path):
    custom_root = tmp_path / "data"
    monkeypatch.setenv("MA_DATA_ROOT", str(custom_root))
    expected = custom_root / "private" / "local_assets" / "historical_echo" / "historical_echo.db"
    assert get_historical_echo_db_path() == expected


def test_hci_v2_dataset_resolvers(monkeypatch, tmp_path):
    t = tmp_path / "targets.csv"
    c = tmp_path / "corpus.csv"
    o = tmp_path / "out.csv"
    monkeypatch.setenv("HCI_V2_TARGETS_CSV", str(t))
    monkeypatch.setenv("HCI_V2_CORPUS_CSV", str(c))
    monkeypatch.setenv("HCI_V2_TRAINING_CSV", str(o))
    assert resolve_hci_v2_targets(None) == t
    assert resolve_hci_v2_corpus(None) == c
    assert resolve_hci_v2_training_out(None) == o


def test_features_output_root_env(monkeypatch, tmp_path):
    custom_root = tmp_path / "data"
    monkeypatch.setenv("MA_DATA_ROOT", str(custom_root))
    assert get_features_output_root() == custom_root / "features_output"


def test_external_data_helpers_respect_env(monkeypatch, tmp_path):
    custom_external = tmp_path / "external"
    monkeypatch.setenv("MA_EXTERNAL_DATA_ROOT", str(custom_external))
    assert get_external_data_root() == custom_external

    year_end = tmp_path / "ye.csv"
    hot100 = tmp_path / "hot.csv"
    core = tmp_path / "core.csv"
    monkeypatch.setenv("MA_KAGGLE_YEAR_END_LYRICS", str(year_end))
    monkeypatch.setenv("MA_HOT100_LYRICS_AUDIO", str(hot100))
    monkeypatch.setenv("MA_CORE1600_CSV", str(core))

    assert get_kaggle_year_end_lyrics_path() == year_end
    assert get_hot100_lyrics_audio_path() == hot100
    assert get_core_1600_csv_path() == core
