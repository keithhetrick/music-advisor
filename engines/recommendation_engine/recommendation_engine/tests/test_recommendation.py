from recommendation_engine.engine.recommendation import (
    classify_hci_band,
    compute_recommendation,
)
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def test_compute_recommendation_basics():
    rec = compute_recommendation(sample_payload, sample_market_norms)
    assert rec["canonical_hci"] == 0.55
    assert rec["hci_band"] == "developing"
    assert rec["axes"]["TempoFit"]["level"] == "low"
    assert rec["features_vs_market"]["tempo_bpm"]["market_position"] == "above_p90"
    assert rec["market_norms_used"]["version"] == "2024-YE"
    assert rec["optimization"], "should produce suggestions"
    summaries = rec.get("intent_summaries") or {}
    for key in ["structure", "groove", "loudness", "mood", "historical", "strategy"]:
        assert key in summaries


def test_classify_hci_band_edges():
    assert classify_hci_band(None) == "unknown"
    assert classify_hci_band(0.2) == "experimental"
    assert classify_hci_band(0.5) == "developing"
    assert classify_hci_band(0.75) == "strong"
    assert classify_hci_band(0.95) == "apex"
