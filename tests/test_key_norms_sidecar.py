from tools.key_norms_sidecar import (
    PITCH_CLASS_NAMES,
    SongKey,
    build_key_advisory,
    build_sidecar_payload,
    compute_lane_stats,
    compute_song_placement,
)


def _sk(root: str, mode: str) -> SongKey:
    return SongKey(root_name=root, mode=mode, pitch_class=PITCH_CLASS_NAMES.index(root))


def test_lane_stats_and_primary_family():
    lane_keys = [
        _sk("C", "major"),
        _sk("C", "major"),
        _sk("G", "major"),
        _sk("A", "minor"),
        _sk("A", "minor"),
        _sk("D", "minor"),
    ]
    stats = compute_lane_stats("tier1_modern", lane_keys, top_k=2)

    assert stats.total_hits == 6
    assert stats.mode_counts["major"] == 3
    assert stats.mode_counts["minor"] == 3
    assert stats.top_keys[0][1] == 2  # top count
    assert "G_major" in stats.primary_family  # fifth neighbor pulled in
    assert "D_minor" in stats.primary_family  # relative neighbor pulled in


def test_song_placement_neighbors():
    lane_keys = [
        _sk("C", "major"),
        _sk("G", "major"),
        _sk("D", "major"),
        _sk("A", "minor"),
        _sk("F", "major"),
    ]
    stats = compute_lane_stats("tier1_modern", lane_keys, top_k=3)
    placement = compute_song_placement(stats, _sk("D", "major"))

    assert placement.same_key_count == 1
    assert placement.same_key_percent > 0
    assert any(nb["key_name"] == "G_major" and nb["distance"] == 1 for nb in placement.neighbor_keys)


def test_advisory_categories():
    lane_keys = [
        _sk("C", "major"),
        _sk("G", "major"),
        _sk("A", "minor"),
        _sk("A", "minor"),
        _sk("F", "major"),
    ]
    stats = compute_lane_stats("tier1_modern", lane_keys, top_k=3)

    primary_adv = build_key_advisory(stats, compute_song_placement(stats, _sk("C", "major")), _sk("C", "major"))
    assert primary_adv.advisory_label == "primary_family"

    adjacent_adv = build_key_advisory(stats, compute_song_placement(stats, _sk("D", "major")), _sk("D", "major"))
    assert adjacent_adv.advisory_label == "adjacent_family"

    sparse_adv = build_key_advisory(stats, compute_song_placement(stats, _sk("F#", "minor")), _sk("F#", "minor"))
    assert sparse_adv.advisory_label == "low_density_key"
    assert sparse_adv.suggested_transpositions  # should offer a small nudge


def test_sidecar_payload_round_trip():
    lane_keys = [
        _sk("C", "major"),
        _sk("G", "major"),
        _sk("A", "minor"),
        _sk("A", "minor"),
    ]
    song_key = _sk("C", "major")
    payload = build_sidecar_payload("tier1_modern", song_key, lane_keys)

    assert payload["key_analysis_version"].startswith("v")
    assert payload["lane_stats"]["total_hits"] == 4
    assert payload["song_placement"]["same_key_count"] == 1
    hist = payload["lane_stats"]["historical_hit_medium"]
    assert hist and hist[0]["key_name"] in ("A_minor", "A minor") and "percent" in hist[0]
    moves = payload["advisory"]["target_key_moves"]
    assert moves and moves[0]["reason"] in {"relative", "parallel"}
    assert "semitone_delta" in moves[0] and "target_key" in moves[0]
    assert payload["advisory"]["advisory_text"]
