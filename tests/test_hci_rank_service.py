from pathlib import Path
import json

from tools.hci.hci_rank_service import (
    RankOptions,
    effective_score,
    filter_entries,
    load_hci_score,
    render_report,
)


def _write_hci(path: Path, score: float, *, sidecar_used: bool, neighbors: bool) -> None:
    feature_meta = {
        "qa_gate": "pass",
        "sidecar_status": "used" if sidecar_used else "missing",
        "tempo_backend_detail": "essentia" if sidecar_used else "librosa",
        "tempo_confidence_score": 0.5,
        "feature_freshness": "ok",
        "audio_feature_freshness": "ok",
    }
    if neighbors:
        hist_meta = {"neighbors_file": "foo.neighbors.json", "neighbors_total": 5}
    else:
        hist_meta = {}
    payload = {
        "HCI_v1_final_score": score,
        "HCI_v1_score_raw": score / 2,
        "feature_pipeline_meta": feature_meta,
        "historical_echo_meta": hist_meta,
    }
    path.write_text(json.dumps(payload))


def test_rank_service_filters_by_sidecar_and_neighbors(tmp_path: Path) -> None:
    """Only entries with used sidecar + neighbors survive strict opts."""
    good = tmp_path / "good.hci.json"
    bad = tmp_path / "bad.hci.json"
    _write_hci(good, 0.8, sidecar_used=True, neighbors=True)
    _write_hci(bad, 0.9, sidecar_used=False, neighbors=False)

    logs = []
    logger = logs.append
    entries = []
    for p in (good, bad):
        res = load_hci_score(p, logger=logger)
        assert res is not None
        entries.append(res)

    opts = RankOptions(
        qa_policy_name="strict",
        require_sidecar_backend="essentia_madmom",
        require_neighbors_file=True,
        top=5,
    )
    filtered, meta = filter_entries(entries, opts, log_warn=logger)
    # Only the good entry remains
    assert len(filtered) == 1
    assert filtered[0]["path"] == good
    assert effective_score(filtered[0]) == filtered[0]["score"]

    status, lines, ranked_entries, top_n, bottom_n = render_report([tmp_path], filtered, opts, meta)
    assert status == 0
    assert ranked_entries == filtered
    assert top_n and top_n[0]["path"] == good
    assert bottom_n and bottom_n[0]["path"] == good
    # Report includes stats and title
    report_text = "\n".join(lines)
    assert "HCI_v1 Ranking Report" in report_text
    assert "good" in report_text
