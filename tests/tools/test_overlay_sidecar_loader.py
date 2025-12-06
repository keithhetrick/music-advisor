import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.overlay_sidecar_loader import load_key_overlay_payload, load_tempo_overlay_payload
from tools.chat import chat_overlay_dispatcher
from tools.chat.overlay_text_helpers import chat_key_summary


def _write_tmp(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_tempo_overlay_payload_missing(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    assert load_tempo_overlay_payload(rich) is None


def test_load_tempo_overlay_payload_minimal(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    tempo = {
        "lane_id": "lane_x",
        "song_bpm": 120.0,
        "lane_stats": {"peak_cluster_bpm_range": [100, 104]},
        "advisory_label": "main_cluster",
        "advisory_text": "test",
    }
    _write_tmp(tmp_path, "song.tempo_norms.json", tempo)
    payload = load_tempo_overlay_payload(rich)
    assert payload is not None
    assert payload["lane_id"] == "lane_x"
    assert payload["hot_zone"] == [100, 104]
    assert payload["advisory"]["text"] == "test"


def test_load_key_overlay_payload_missing(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    assert load_key_overlay_payload(rich) is None


def test_load_key_overlay_payload_minimal(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    key = {
        "lane_id": "lane_y",
        "song_key": {"root_name": "C", "mode": "major"},
        "lane_stats": {"primary_family": ["C_major"], "lane_shape": {"entropy": 1.0}},
        "advisory": {"advisory_text": "ok"},
    }
    _write_tmp(tmp_path, "song.key_norms.json", key)
    payload = load_key_overlay_payload(rich, top_target_moves=2)
    assert payload is not None
    assert payload["lane_id"] == "lane_y"
    assert payload["lane_shape"]["entropy"] == 1.0
    assert payload["advisory"]["text"] == "ok"
    summary = chat_key_summary(payload, max_targets=2)
    assert len(summary["target_key_moves"]) <= 2


def test_load_with_top_n_trim(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    tempo = {
        "lane_id": "lane_z",
        "song_bpm": 120.0,
        "lane_stats": {"peak_cluster_bpm_range": [100, 104]},
        "neighbor_bins": [{"center_bpm": 90, "hit_count": 1}, {"center_bpm": 110, "hit_count": 2}],
        "advisory_text": "test",
    }
    _write_tmp(tmp_path, "song.tempo_norms.json", tempo)
    payload = load_tempo_overlay_payload(rich, top_neighbor_bins=1)
    assert payload is not None
    assert len(payload["neighbor_bins"]) == 1


def test_dispatcher_unknown_intent(tmp_path: Path):
    rich = tmp_path / "song.client.rich.txt"
    rich.write_text("# dummy\n", encoding="utf-8")
    resp = chat_overlay_dispatcher.handle_intent("unknown", rich)
    assert "Unknown intent" in resp
