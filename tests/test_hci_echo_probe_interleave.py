from tools.hci_echo_probe_from_spine_v1 import select_top_neighbors


def test_select_top_neighbors_interleaves_tiers():
    rows = [
        {"tier": "tier1_modern", "distance": 0.10, "artist": "A1", "title": "T1"},
        {"tier": "tier1_modern", "distance": 0.40, "artist": "A1b", "title": "T1b"},
        {"tier": "tier2_modern", "distance": 0.20, "artist": "B2", "title": "T2"},
        {"tier": "tier2_modern", "distance": 0.50, "artist": "B2b", "title": "T2b"},
        {"tier": "tier3_modern", "distance": 0.30, "artist": "C3", "title": "T3"},
        {"tier": "tier3_modern", "distance": 0.60, "artist": "C3b", "title": "T3b"},
    ]

    selected = select_top_neighbors(rows, top_k=6)

    # Expect round-robin across tiers in priority order, not all tier1 first.
    tier_sequence = [r["tier"] for r in selected]
    assert tier_sequence[:4] == [
        "tier1_modern",
        "tier2_modern",
        "tier3_modern",
        "tier1_modern",
    ]
    # And all tiers are represented in the final set.
    assert set(tier_sequence) == {"tier1_modern", "tier2_modern", "tier3_modern"}


def test_select_top_neighbors_dedup_by_slug():
    rows = [
        {"tier": "tier1_modern", "distance": 0.10, "artist": "Same", "title": "Song"},
        {"tier": "tier2_modern", "distance": 0.05, "artist": "Same", "title": "Song"},  # duplicate slug
        {"tier": "tier2_modern", "distance": 0.20, "artist": "Other", "title": "Song2"},
    ]

    selected = select_top_neighbors(rows, top_k=3)

    # Should keep only one of the duplicate slug entries (the first encountered).
    assert len([r for r in selected if r["title"] == "Song"]) == 1
    assert any(r["title"] == "Song2" for r in selected)
