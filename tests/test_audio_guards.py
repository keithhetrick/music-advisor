import math
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


def _write_sine(path: Path, duration_sec: float = 2.0, sr: int = 8000) -> Path:
    """Write a small sine tone for duration checks."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    y = 0.1 * np.sin(2 * math.pi * 440 * t)
    sf.write(path, y, sr)
    return path


def test_analyze_pipeline_rejects_excessive_duration(tmp_path, monkeypatch):
    """Duration guard should fail before heavy decode when over cap."""
    from tools.audio import ma_audio_features as maf

    audio = _write_sine(tmp_path / "too_long.wav", duration_sec=2.0)
    monkeypatch.setattr(maf, "MAX_AUDIO_DURATION_SEC", 1.0)

    with pytest.raises(RuntimeError, match="duration too long"):
        maf.analyze_pipeline(path=str(audio), use_cache=False)


def test_analyze_pipeline_rejects_invalid_audio(tmp_path):
    """Non-audio payload with audio extension should fail preflight when probe is available."""
    from tools.audio import ma_audio_features as maf

    bad = tmp_path / "not_audio.wav"
    bad.write_text("this is not audio")
    with pytest.raises(RuntimeError, match="preflight failed"):
        maf.analyze_pipeline(path=str(bad), use_cache=False)


def test_sidecar_custom_command_blocked_without_opt_in(tmp_path):
    """Custom sidecar templates should be blocked unless explicitly allowed."""
    from tools import sidecar_adapter as sa

    payload, out_path, warnings = sa.run_sidecar(
        audio_path=str(tmp_path / "dummy.wav"),
        cmd_template="echo should_not_run > {out}",
        allow_custom_cmd=False,
    )
    assert payload is None
    assert out_path is None
    assert "sidecar_custom_cmd_blocked" in warnings


def test_sidecar_timeout_returns_warning(tmp_path):
    """Sidecar commands should time out promptly."""
    from tools import sidecar_adapter as sa
    from security.config import CONFIG as SEC_CONFIG
    from pathlib import Path

    dummy_audio = tmp_path / "dummy.wav"
    dummy_audio.write_bytes(b"\0")
    python_bin = SEC_CONFIG.repo_root / ".venv/bin/python"
    payload, out_path, warnings = sa.run_sidecar(
        audio_path=str(dummy_audio),
        cmd_template=f"{python_bin} -c \"import time; time.sleep(2)\" {{audio}} {{out}}",
        allow_custom_cmd=True,
        timeout_seconds=0.1,
    )
    assert payload is None
    assert out_path is None
    assert any(w in {"sidecar_timeout", "sidecar_subprocess_error"} for w in warnings)
