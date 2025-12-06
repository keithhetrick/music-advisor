import json
import os
import subprocess
import sys
import wave, struct
from pathlib import Path

def test_payload_has_axes_and_ttc(tmp_path: Path):
    audio = tmp_path / 's.wav'
    sr = 44100
    with wave.open(str(audio), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = int(sr * 0.1)
        wf.writeframes(b''.join(struct.pack('<h', 0) for _ in range(frames)))

    out = tmp_path / 'p.json'
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{repo}:{repo/'src'}"
    cmd = [
        sys.executable,
        str(repo / 'tools' / 'ma_audio_features.py'),
        '--audio', str(audio),
        '--out', str(out),
    ]
    subprocess.check_call(cmd, env=env)
    payload = json.loads(out.read_text())
    assert 'tempo_bpm' in payload
    assert 'duration_sec' in payload
    assert 'tempo_confidence_score' in payload or 'tempo_confidence_score_raw' in payload
