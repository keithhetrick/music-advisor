import json
from pathlib import Path

from advisor_host.adapter.adapter import parse_helper_text
from advisor_host.host.advisor import classify_hci_band, run_advisory, select_canonical_hci


def test_select_canonical_hci_priority():
    payload = {
        "HCI_audio_v2": {"score": 0.5},
        "HCI_v1_score": 0.7,
        "HCI_v1_final_score": 0.8,
    }
    score, source = select_canonical_hci(payload)
    assert score == 0.8
    assert source == "HCI_v1_final_score"


def test_run_advisory_missing_hci():
    payload = {
        "features_full": {"tempo_bpm": 100.0, "duration_sec": 200, "loudness_LUFS": -9.0},
        "audio_axes": {"TempoFit": 0.8, "RuntimeFit": 0.7, "LoudnessFit": 0.6},
    }
    result = run_advisory(payload)
    assert result["canonical_hci"] is None
    assert result["hci_band"] == "unknown"
    assert result["axes"]["TempoFit"]["level"] == "high"
    assert result["warnings"]  # should contain missing HCI warning


def test_parse_helper_text_simple():
    txt = "/audio import {\"region\":\"US\",\"features_full\":{},\"audio_axes\":{}}"
    payload = parse_helper_text(txt)
    assert payload["region"] == "US"


def test_classify_hci_band_boundaries():
    assert classify_hci_band(None) == "unknown"
    assert classify_hci_band(0.2) == "experimental"
    assert classify_hci_band(0.5) == "developing"
    assert classify_hci_band(0.75) == "strong"
    assert classify_hci_band(0.95) == "apex"


def test_run_advisory_with_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "sample_client.json"
    payload = json.loads(fixture_path.read_text())
    result = run_advisory(payload)
    assert result["canonical_hci"] == 0.81
    assert result["hci_band"] == "strong"
    assert result["axes"]["TempoFit"]["level"] == "high"
    assert result["historical_echo"]["available"] is True
