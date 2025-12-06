import json
import os
import subprocess
import sys
import wave
import struct
import math
from pathlib import Path


def _make_tone(path: Path, sr: int = 44100, freq: float = 440.0, dur: float = 1.0) -> None:
    n = int(sr * dur)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for i in range(n):
            val = int(0.2 * 32767 * math.sin(2 * math.pi * freq * i / sr))
            w.writeframes(struct.pack("<h", val))


def test_smoke_full_chain_with_stub_sidecar(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    tone = tmp_path / "tone.wav"
    _make_tone(tone)
    db_path = repo / "data" / "private" / "local_assets" / "historical_echo" / "historical_echo.db"
    if not db_path.exists():
        import pytest
        pytest.skip(f"historical_echo.db not available at {db_path}")
    env = os.environ.copy()
    env.update({"LOG_JSON": "0", "MA_SIDECAR_PLUGIN": "stub", "PYTHONPATH": f"{repo}:{repo/'src'}"})
    cmd = ["zsh", str(repo / "infra" / "scripts" / "smoke_full_chain.sh"), str(tone)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    out_dir_root = Path("data/features_output/smoke")
    assert out_dir_root.exists()
    all_runs = list(out_dir_root.glob("*/*"))
    assert all_runs, "no smoke output found under features_output/smoke"
    latest = max(all_runs, key=lambda p: p.stat().st_mtime)
    run_summary = latest / "run_summary.json"
    assert run_summary.exists()
    summary = json.loads(run_summary.read_text())
    # Artifacts should include at least features/merged/hci/neighbors plus helper payloads.
    artifacts = summary.get("artifacts", {})
    for key in ("features", "merged", "hci", "neighbors"):
        assert key in artifacts, f"missing artifact {key}"
    assert ("client_json" in artifacts), "missing helper json (client)"
    assert ("client_rich" in artifacts), "missing rich txt (client)"
