from pathlib import Path
import json

from tools.hci.hci_rank_service import (
    RankOptions,
    filter_entries,
    load_hci_score,
    render_report,
)


def _write_hci(path: Path, score: float) -> None:
    payload = {
        "HCI_v1_final_score": score,
        "HCI_v1_score_raw": score / 2,
        "HCI_v1_final_tier": "WIP-A",
        "feature_pipeline_meta": {
            "qa_gate": "pass",
            "sidecar_status": "used",
            "tempo_backend_detail": "essentia",
            "tempo_confidence_score": 0.5,
            "feature_freshness": "ok",
            "audio_feature_freshness": "ok",
        },
        "historical_echo_meta": {
            "neighbors_file": "dummy.neighbors.json",
            "neighbors_total": 5,
            "neighbor_tiers": ["tier1_modern"],
            "neighbors_kept_inline": 4,
        },
    }
    path.write_text(json.dumps(payload))


def test_rank_service_end_to_end(tmp_path: Path) -> None:
    high = tmp_path / "high.hci.json"
    low = tmp_path / "low.hci.json"
    _write_hci(high, 0.8)
    _write_hci(low, 0.4)

    logs = []
    logger = logs.append
    entries = []
    for p in (high, low):
        res = load_hci_score(p, logger=logger)
        assert res is not None
        entries.append(res)

    opts = RankOptions(
        qa_policy_name="strict",
        require_sidecar_backend="essentia_madmom",
        require_neighbors_file=True,
        top=2,
    )
    filtered, meta = filter_entries(entries, opts, log_warn=logger)
    assert len(filtered) == 2
    status, lines, ranked, top_n, bottom_n = render_report([tmp_path], filtered, opts, meta)
    assert status == 0
    assert ranked[0]["path"] == high
    assert top_n[0]["path"] == high
    assert bottom_n[-1]["path"] == low
    report = "\n".join(lines)
    assert "HCI_v1 Ranking Report" in report
    assert "Top 2" in report
