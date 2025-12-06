import json
import sqlite3

import pytest

from ma_lyrics_engine.schema import ensure_schema
from tools import names
from tools.ma_merge_client_and_hci import load_tempo_overlay_block
from tools.tempo_norms_sidecar import build_sidecar_payload, compute_lane_stats, load_lane_bpms


def test_compute_lane_stats_peak_cluster():
    bpms = [90, 92, 92, 94, 95, 100, 102]
    stats, counts, clusters, shape = compute_lane_stats("tier1_modern", bpms, bin_width=2.0)
    assert stats.total_hits == len(bpms)
    assert stats.median_bpm == pytest.approx(94.0)
    assert stats.iqr_low == pytest.approx(92.0)
    assert stats.iqr_high == pytest.approx(97.5)
    assert stats.peak_cluster_min == pytest.approx(92.0)
    assert stats.peak_cluster_max == pytest.approx(96.0)
    assert counts[93.0] == 2
    assert max(counts.values()) == 2


def test_advisory_labels_across_clusters():
    lane_bpms = [98, 99, 100, 100, 101, 101, 102, 104, 105, 120, 122]
    payload_main = build_sidecar_payload("tier1_modern", 100.0, 2.0, lane_bpms)
    assert payload_main["advisory_label"] == "main_cluster"

    payload_edge = build_sidecar_payload("tier1_modern", 98.0, 2.0, lane_bpms)
    assert payload_edge["advisory_label"] == "edge_cluster"

    payload_sparse = build_sidecar_payload("tier1_modern", 80.0, 2.0, lane_bpms)
    assert payload_sparse["advisory_label"] == "low_density_pocket"
    assert payload_sparse["suggested_bpm_range"]


def test_lane_loader_and_overlay_round_trip(tmp_path):
    db_path = tmp_path / "lane.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO songs (song_id, title, artist, year, peak_position, weeks_on_chart, source, tier, era_bucket) VALUES (?,?,?,?,?,?,?,?,?)",
        ("song1", "Title", "Artist", 2020, 10, 12, "hot100", 1, "2015_2024"),
    )
    conn.execute(
        "INSERT INTO songs (song_id, title, artist, year, peak_position, weeks_on_chart, source, tier, era_bucket) VALUES (?,?,?,?,?,?,?,?,?)",
        ("song2", "Other", "Artist", 2020, 80, 12, "hot100", 2, "2015_2024"),
    )
    conn.execute("INSERT INTO features_song (song_id, tempo_bpm) VALUES (?, ?)", ("song1", 100.0))
    conn.execute("INSERT INTO features_song (song_id, tempo_bpm) VALUES (?, ?)", ("song2", 140.0))
    conn.commit()

    bpms = load_lane_bpms(conn, "tier1__2015_2024")
    assert bpms == [100.0]

    payload = build_sidecar_payload("tier1__2015_2024", 100.0, 2.0, bpms)
    round_trip = json.loads(json.dumps(payload))
    assert round_trip["lane_stats"]["total_hits"] == 1
    assert round_trip["song_bin"]["hit_count"] == 1

    sidecar_path = tmp_path / f"song1{names.tempo_norms_sidecar_suffix()}"
    sidecar_path.write_text(json.dumps(payload))
    overlay = load_tempo_overlay_block("song1", tmp_path)
    assert overlay is not None
    assert "TEMPO LANE OVERLAY" in overlay
    conn.close()
