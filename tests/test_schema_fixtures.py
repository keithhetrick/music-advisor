from pathlib import Path
import json
from ma_audio_engine import schemas
from shared.ma_utils import schema_utils


def test_golden_features_and_hci_lint_clean():
    root = Path("tests/fixtures")
    feat = root / "golden.features.json"
    hci = root / "golden.hci.json"
    warn_f, _ = schema_utils.lint_json_file(feat, "features")
    warn_h, _ = schema_utils.lint_json_file(hci, "hci")
    assert warn_f == []
    assert warn_h == []


def test_golden_sidecar_lint_clean():
    root = Path("tests/fixtures")
    sidecar = root / "golden.sidecar.json"
    warns = schemas.lint_sidecar_payload(json.loads(sidecar.read_text()))
    assert warns == []


def test_golden_merged_neighbors_and_summary_clean():
    root = Path("tests/fixtures")
    merged = root / "golden.merged.json"
    neighbors = root / "golden.neighbors.json"
    summary = root / "golden.run_summary.json"
    warn_m, _ = schema_utils.lint_json_file(merged, "merged")
    warn_n, _ = schema_utils.lint_json_file(neighbors, "neighbors")
    warn_s, _ = schema_utils.lint_json_file(summary, "run_summary")
    assert warn_m == []
    assert warn_n == []
    assert warn_s == []


def test_golden_client_rich_lint_clean():
    root = Path("tests/fixtures")
    client = root / "golden.client.rich.txt"
    warns = schemas.lint_client_rich_text(client.read_text())
    assert warns == []
