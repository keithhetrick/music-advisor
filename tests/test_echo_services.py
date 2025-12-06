from pathlib import Path
from tools.echo_services import inject_echo_into_hci, inject_echo_into_client


def _sample_echo():
    return {
        "neighbors": [
            {"tier": "tier1_modern", "distance": 0.1, "year": 2000, "artist": "A", "title": "T"}
        ],
        "decade_counts": {"1995–2004": 1},
    }


def test_inject_echo_into_hci(tmp_path: Path):
    hci = {}
    feat_meta = {"source_hash": "x", "config_fingerprint": "y", "pipeline_version": "v"}
    updated, warns = inject_echo_into_hci(hci, feat_meta, _sample_echo(), tmp_path / "neighbors.json")
    assert "historical_echo_v1" in updated
    assert updated["historical_echo_meta"]["neighbors_total"] == 1
    assert isinstance(warns, list)


def test_inject_echo_into_client(tmp_path: Path):
    client = {}
    client_out, warns, bundle = inject_echo_into_client(client, None, None, _sample_echo(), tmp_path / "neighbors.json")
    assert "historical_echo_v1" in client_out
    assert "neighbor_lines" in bundle
    assert isinstance(warns, list)
