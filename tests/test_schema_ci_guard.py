import json
from pathlib import Path

import pytest

from tools.schema_utils import lint_json_file


@pytest.fixture
def tmp_pack(tmp_path: Path) -> Path:
    data = {
        "audio_name": "demo",
        "region": "US",
        "profile": "Pop",
        "generated_by": "test",
        "inputs": {"paths": {"source_audio": "demo.wav"}, "merged_features_present": True, "lyric_axis_present": False, "internal_features_present": True},
        "features": {"tempo_bpm": 120, "energy": 0.5, "danceability": 0.5, "valence": 0.5, "loudness_LUFS": -12, "key": "C", "mode": "major", "runtime_sec": 180},
        "features_full": {"bpm": 120, "mode": "major", "key": "C", "duration_sec": 180, "runtime_sec": 180, "loudness_lufs": -12, "energy": 0.5, "danceability": 0.5, "valence": 0.5},
    }
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def tmp_neighbors(tmp_path: Path) -> Path:
    data = {
        "neighbors": [
            {
                "tier": "tier1_modern",
                "artist": "Test",
                "title": "Song",
                "year": 2000,
                "tempo": 120,
                "valence": 0.5,
                "energy": 0.5,
                "loudness": -12.0,
                "distance": 0.1,
                "feature_source": "essentia_local",
            }
        ],
        "decade_counts": {"1995–2004": 1},
    }
    path = tmp_path / "neighbors.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def tmp_run_summary(tmp_path: Path) -> Path:
    data = {
        "out_dir": "/tmp/demo",
        "pipeline_version": "test",
        "versions": {"numpy": "1.0"},
        "warnings": [],
        "artifacts": {"features": {"kind": "features", "path": "demo.json", "bytes": 10}},
    }
    path = tmp_path / "run_summary.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize(
    "kind_fixture",
    [
        ("pack", "tmp_pack"),
        ("neighbors", "tmp_neighbors"),
        ("run_summary", "tmp_run_summary"),
    ],
)
def test_schema_guard(kind_fixture, request):
    kind, fixture_name = kind_fixture
    path = request.getfixturevalue(fixture_name)
    warnings, _ = lint_json_file(path, kind)
    assert not warnings, f"{kind} lint warnings: {warnings}"
