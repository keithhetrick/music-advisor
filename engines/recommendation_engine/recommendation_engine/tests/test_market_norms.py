from pathlib import Path

from recommendation_engine.market_norms import get_market_norms, load_snapshot


def test_get_market_norms_latest(tmp_path):
    root = tmp_path / "market_norms"
    root.mkdir()
    (root / "US_Tier1_2024-YE.json").write_text('{"region":"US","tier":"Tier1","version":"2024-YE"}')
    (root / "US_Tier1_2025-01.json").write_text('{"region":"US","tier":"Tier1","version":"2025-01"}')
    snap = get_market_norms("US", "Tier1", version="latest", root=root)
    assert snap.version == "2025-01"
    snap_explicit = get_market_norms("US", "Tier1", version="2024-YE", root=root)
    assert snap_explicit.version == "2024-YE"


def test_load_snapshot():
    fixture = Path("engines/recommendation_engine/recommendation_engine/tests/fixtures/market_norms_us_tier1_2024YE.json")
    snap = load_snapshot(fixture)
    assert snap.region == "US"
    assert snap.payload["version"] == "2024-YE"
