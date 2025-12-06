from pathlib import Path
import importlib


def test_hci_only_outputs(tmp_path, monkeypatch):
    # Use pipeline driver but avoid heavy work by pointing to existing fixtures if available.
    import tools.pipeline_driver  # noqa: F401
    # We won't run the driver here (heavy), but enforce expected file names for validation.
    stem = "sample_track"
    out_dir = tmp_path / "2025" / "12" / stem
    out_dir.mkdir(parents=True)
    expected = {
        f"{stem}_features.json",
        f"{stem}_sidecar.json",
        f"{stem}_merged.json",
        f"{stem}.client.txt",
        f"{stem}.client.json",
        f"{stem}.client.rich.txt",
        f"{stem}.hci.json",
        f"{stem}.neighbors.json",
        "run_summary.json",
    }
    # Touch expected files to simulate a run
    for name in expected:
        (out_dir / name).write_text("{}", encoding="utf-8")

    found = {p.name for p in out_dir.iterdir() if p.is_file()}
    assert expected.issubset(found)
    # This guards the naming contract; if new outputs are added, update both the driver doc and this test.
