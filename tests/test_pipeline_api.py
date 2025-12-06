from pathlib import Path
import json

from tools import pipeline_api


def test_run_merge_and_pack(tmp_path: Path):
    merged = {
        "source_audio": "song.wav",
        "duration_sec": 180,
        "tempo_bpm": 120,
        "key": "C",
        "mode": "major",
        "loudness_LUFS": -10.0,
    }
    merged_result, warns = pipeline_api.run_merge(merged, None)
    assert merged_result["tempo_bpm"] == 120
    assert isinstance(warns, list)

    out_dir = tmp_path / "out"
    pack = pipeline_api.run_pack(
        merged_result,
        out_dir,
        write_pack=False,
        client_json=out_dir / "c.json",
        client_txt=out_dir / "c.txt",
    )
    assert pack["audio_name"] == "song"
    assert (out_dir / "c.json").exists()
    assert (out_dir / "c.txt").exists()


def test_run_merge_client_hci():
    pack = {"audio_name": "song", "region": "US", "profile": "Pop"}
    hci = {"HCI_v1_final_score": 0.5, "HCI_v1_role": "unknown"}
    merged, rich, warns = pipeline_api.run_merge_client_hci(pack, hci)
    assert merged["HCI_v1_final_score"] == 0.5
    assert "HCI_V1_SUMMARY" in rich
    assert isinstance(warns, list)
