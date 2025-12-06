# tests/test_baseline_advisory_off.py
import json, os, subprocess, pathlib, sys

def test_advisory_absent_when_disabled(tmp_path, monkeypatch):
    # 1s tone
    import math, wave, struct
    wav = tmp_path/"tone.wav"; sr=44100; n=int(sr*1.0)
    with wave.open(str(wav),"w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        for i in range(n): w.writeframes(struct.pack("<h", int(0.2*32767*math.sin(2*math.pi*440*i/sr))))
    monkeypatch.setenv("MA_DISABLE_NORMS_ADVISORY","1")
    out = tmp_path/"advisory.json"
    cmd = [
        sys.executable,
        "-m",
        "ma_audio_engine.pipe_cli",
        "--audio",
        str(wav),
        "--market",
        "0.48",
        "--emotional",
        "0.67",
        "--round",
        "3",
        "--out",
        str(out),
    ]
    subprocess.check_call(cmd)
    d = json.loads(out.read_text())
    b = d.get("Baseline", {})
    assert "advisory" not in b
