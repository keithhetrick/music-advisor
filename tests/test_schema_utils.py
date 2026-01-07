from shared.ma_utils import schema_utils
from tools.audio import ma_audio_features as maf


def test_lint_hci_requires_meta_and_score():
    warnings = schema_utils.lint_hci_payload({})
    assert "missing:feature_pipeline_meta" in warnings
    assert any(w.startswith("missing_or_non_numeric:HCI_v1_final_score") or w == "missing:HCI_v1_final_score" for w in warnings)


def test_pad_short_signal_pads_to_min_len():
    import numpy as np

    y = np.ones(10)
    padded = maf._pad_short_signal(y, min_len=32, label="test")
    assert len(padded) == 32
    assert padded[:10].tolist() == y.tolist()


def test_log_summary_detects_artifacts(tmp_path):
    # Create fake artifacts
    out_dir = tmp_path / "track"
    out_dir.mkdir()
    for name in ["a.features.json", "b.sidecar.json", "c.merged.json", "d.hci.json", "e.client.json", "f.client.rich.txt", "g.neighbors.json"]:
        (out_dir / name).write_text("{}")
    from tools import log_summary
    import json

    log_summary.main(["--out-dir", str(out_dir)])
    summary = json.loads((out_dir / "run_summary.json").read_text())
    assert "artifacts" in summary
    assert summary["artifacts"].get("features")
