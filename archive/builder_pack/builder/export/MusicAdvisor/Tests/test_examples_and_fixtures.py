import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sample_payload_minimal_has_required_fields():
    sample = ROOT / "Examples" / "sample_payload_minimal.json"
    data = json.loads(sample.read_text())
    assert "audio_axes" in data and len(data["audio_axes"]) == 6
    assert "MARKET_NORMS" in data
    assert data["MARKET_NORMS"].get("profile")
    assert "TTC" in data and "seconds" in data["TTC"]


def test_fixtures_have_market_norms_and_ids():
    fixtures_dir = ROOT / "QA"
    fixtures = [p for p in fixtures_dir.glob("*.fixture.json") if p.name != "_Template.fixture.json"]
    assert fixtures, "No QA fixtures found"

    for fx in fixtures:
        blob = json.loads(fx.read_text())
        assert blob.get("id"), f"missing id in {fx.name}"
        mn = blob.get("MARKET_NORMS") or {}
        assert mn.get("profile"), f"missing MARKET_NORMS.profile in {fx.name}"
        # Basic required fields for routing
        assert blob.get("region"), f"missing region in {fx.name}"
        assert blob.get("genre"), f"missing genre in {fx.name}"
