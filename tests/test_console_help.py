import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "cmd",
    [
        ["-m", "tools.lyric_stt_sidecar", "--help"],
        ["-m", "tools.lyric_wip_pipeline", "--help"],
        ["-m", "tools.ttc_sidecar", "--help"],
        ["-m", "tools.lyric_neighbors", "--help"],
        ["-m", "tools.song_context_builder", "--help"],
    ],
)
def test_console_help_runs(cmd):
    """Smoke check: key CLIs respond to --help without errors."""
    proc = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    assert proc.returncode == 0, f"Help failed for {cmd}: {proc.stderr}"
    assert "usage" in proc.stdout.lower()
