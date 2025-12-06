import csv
import json
from pathlib import Path

from tools import hci_compare_targets as hci_compare


def test_loaders_join_local_and_targets(tmp_path):
    # Targets CSV with one row
    target_csv = tmp_path / "targets.csv"
    with target_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "artist", "title", "year_end_rank"])
        writer.writeheader()
        writer.writerow(
            {"year": 1985, "artist": "Test Artist", "title": "My Song", "year_end_rank": 10}
        )

    # Local tree with HCI + features sidecar
    root = tmp_path / "features_output"
    hci_dir = root / "1985" / "1985_test_artist__my_song"
    hci_dir.mkdir(parents=True)

    hci_path = hci_dir / "1985_test_artist__my_song__single.hci.json"
    hci_blob = {"HCI_v1": {"score": 0.5, "raw": 0.55, "axes": {"LoudnessFit": 0.4}}}
    hci_path.write_text(json.dumps(hci_blob))

    feat_path = hci_dir / "1985_test_artist__my_song__single.features.json"
    feat_blob = {
        "tempo_bpm": 120.0,
        "duration_sec": 180.0,
        "loudness_LUFS": -18.0,
        "danceability": 0.6,
        "energy": 0.7,
        "valence": 0.4,
    }
    feat_path.write_text(json.dumps(feat_blob))

    targets, fieldnames = hci_compare.load_targets(target_csv, years=[1985], max_rank=50)
    local, axes = hci_compare.load_local(root, years=[1985])

    assert fieldnames == ["year", "artist", "title", "year_end_rank"]
    assert len(targets) == 1
    assert len(local) == 1
    assert "LoudnessFit" in axes

    key = next(iter(local))
    assert key in targets

    lr = local[key]
    assert lr.hci_score == 0.5
    assert lr.tempo_bpm == 120.0
    assert lr.duration_sec == 180.0
    assert lr.loudness_LUFS == -18.0
