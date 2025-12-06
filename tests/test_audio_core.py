# tests/test_audio_core.py

import os
import math
import wave
import struct
from pathlib import Path

from ma_audio_engine.analyzers.audio_core import analyze_basic_features, _tempo_band


def _write_tone(path: str, sr=44100, freq=440.0, dur=1.0, amp=0.2):
    n = int(sr * dur)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for i in range(n):
            s = int(amp * 32767 * math.sin(2 * math.pi * freq * i / sr))
            w.writeframes(struct.pack("<h", s))


def test_basic_features_exist(tmp_path: Path):
    p = tmp_path / "tone.wav"
    _write_tone(str(p), dur=1.0)
    feats = analyze_basic_features(str(p), sr=44100)

    assert "duration_sec" in feats
    assert abs(feats["duration_sec"] - 1.0) < 0.05

    assert "tonal" in feats and isinstance(feats["tonal"], dict)
    assert 0.0 <= feats["tonal"]["confidence"] <= 1.0

    # tempo may be None on 1-second tones; that's acceptable
    assert "tempo" in feats
    if feats["tempo"] is not None:
        assert 40 <= feats["tempo"]["bpm"] <= 220
        assert isinstance(feats["tempo"]["band"], str)


def test_tempo_band_format():
    assert _tempo_band(86.2) == "80-89"
    assert _tempo_band(120.0) == "120-129"
