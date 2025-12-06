from pathlib import Path
import json
from tools.philosophy_services import inject_philosophy_into_hci, inject_philosophy_line_into_client, build_philosophy_line


def test_inject_philosophy_into_hci():
    data, warns = inject_philosophy_into_hci({}, force=False)
    assert "HCI_v1_philosophy" in data
    assert warns == []


def test_inject_philosophy_line_into_client():
    text = "# HCI_V1_SUMMARY: final=0.5\n/audo import {}"
    line = "# PHILOSOPHY: test HCI_v1 is a measure..."
    out = inject_philosophy_line_into_client(text, line)
    assert "PHILOSOPHY" in out


def test_build_philosophy_line_defaults(tmp_path: Path):
    hci = tmp_path / "track.hci.json"
    hci.write_text('{"HCI_v1_philosophy": {"tagline": "custom"}}')
    line = build_philosophy_line("default", hci)
    assert "custom" in line


def test_process_client_file_inserts_line(tmp_path: Path):
    # Import inside the test to avoid importing adapters at module import time.
    from tools import ma_add_philosophy_to_client_rich as client_philo

    client = tmp_path / "song.client.rich.txt"
    hci = tmp_path / "song.hci.json"
    # Provide a philosophy tagline in the matching HCI file.
    hci.write_text(json.dumps({"HCI_v1_philosophy": {"tagline": "Inline Tagline"}}))
    payload = {
        "region": "US",
        "profile": "Pop",
        "audio_name": "song",
        "generated_by": "test",
        "inputs": {
            "paths": {"source_audio": "song.mp3"},
            "merged_features_present": True,
            "lyric_axis_present": False,
            "internal_features_present": True,
        },
        "features": {
            "tempo_bpm": 120,
            "key": "C",
            "mode": "major",
            "duration_sec": 180,
            "loudness_LUFS": -12,
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
        },
    }
    client.write_text(
        "\n".join(
            [
                "# HCI_V1_SUMMARY: final=0.5 | role=unknown | raw=0.5 | calibrated=0.5",
                "/audio import " + json.dumps(payload, indent=2),
            ]
        )
        + "\n"
    )
    updated, warns = client_philo.process_client_file(client, default_tagline=client_philo.DEFAULT_TAGLINE)
    assert updated is True
    text = client.read_text()
    assert "Inline Tagline" in text
    assert "PHILOSOPHY" in text
