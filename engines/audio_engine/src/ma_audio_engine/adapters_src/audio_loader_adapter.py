"""
Audio loader adapter: keeps audio loading swappable via config/audio_loader.json.

Defaults:
- backend: librosa
- mono: True
- max ffmpeg decode duration: MAX_AUDIO_DURATION_SEC env (default 900s)

Config:
- file: config/audio_loader.json (keys: backend, mono)
- env: MAX_AUDIO_DURATION_SEC caps ffmpeg fallback duration.

Usage:
- `load_audio_mono(path, sr=44100)` loads mono audio (librosa, then ffmpeg fallback).
- Override backend/mono via config file if additional backends are added later.

Notes:
- Side effects: uses ffprobe/ffmpeg subprocesses and writes a temporary WAV during fallback.
- Security: ffprobe/ffmpeg inputs are validated against allowed formats from SEC_CONFIG; duration capped to avoid runaway decodes.
- Errors: raises RuntimeError on missing ffmpeg/ffprobe, invalid format, or decode failures.
- If you add new backends, document their env/config knobs and error behavior here.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import shutil

import numpy as np
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "audio_loader.json"
_DEFAULT_BACKEND = "librosa"
_DEFAULT_MONO = True
_MAX_FFMPEG_DURATION_SEC = int(os.environ.get("MAX_AUDIO_DURATION_SEC", "900"))

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict):
            if isinstance(data.get("backend"), str):
                _DEFAULT_BACKEND = data["backend"]
            if isinstance(data.get("mono"), bool):
                _DEFAULT_MONO = data["mono"]
except Exception:
    # Optional config; fall back silently.
    pass


def load_audio_mono(path: str, sr: int = 44100, backend: Optional[str] = None) -> Tuple[np.ndarray, int]:
    """
    Load mono audio using the configured backend. Currently supports librosa only.

    Steps:
    1) Try librosa load (mono flag respected).
    2) On failure, probe with ffprobe (format guard) and decode via ffmpeg to temp WAV (duration-capped).
    3) Load decoded WAV with librosa; return float32 array and sample rate.

    Raises RuntimeError when decode/probe fails or backend unsupported.
    """
    backend = (backend or _DEFAULT_BACKEND or "librosa").lower()
    mono = _DEFAULT_MONO
    if backend == "librosa":
        import librosa  # lazy import to keep optional

        try:
            y, sr_out = librosa.load(path, sr=sr, mono=mono)
            if y is not None and len(y) > 0:
                return np.asarray(y, dtype=np.float32), sr_out
        except Exception:
            # Fall through to ffmpeg decode
            pass
        # Fallback: validate/probe before decode via ffmpeg, cap duration to avoid runaway decodes
        if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
            raise RuntimeError(f"ffmpeg/ffprobe not available for fallback decode: {path}")
        try:
            # sanity probe; best-effort format/duration check
            probe = sec_subprocess.run_safe(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name", "-of", "default=noprint_wrappers=1:nokey=1", path],
                allow_roots=SEC_CONFIG.allowed_binary_roots,
                timeout=SEC_CONFIG.subprocess_timeout,
                check=True,
                capture_output=True,
            )
            fmt = None
            if probe.stdout:
                lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
                if lines:
                    # Prefer a non-numeric token as format; ffprobe sometimes emits duration after format_name
                    for token in reversed(lines):
                        # If token has any alpha chars, treat as format
                        if any(c.isalpha() for c in token):
                            fmt = token
                            break
                    if fmt is None:
                        fmt = lines[-1]
            if fmt:
                # ffprobe may emit comma-separated formats; accept if any token matches allowed formats
                tokens = {t.strip().lower() for t in fmt.split(",") if t.strip()}
                allowed_formats = {f.lstrip(".").lower() for f in SEC_CONFIG.allowed_formats}
                if tokens.isdisjoint(allowed_formats):
                    raise RuntimeError(f"ffprobe format not allowed: {fmt}")
        except Exception:
            raise RuntimeError(f"ffprobe failed to parse or validate audio: {path}")

        # Decode via ffmpeg to a temp WAV then load, with a duration cap
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        try:
            # ffmpeg may emit to stderr; suppress unless needed
            cmd = [
                "ffmpeg",
                "-y",
                "-t",
                str(_MAX_FFMPEG_DURATION_SEC),
                "-i",
                path,
                "-ac",
                "1",
                "-ar",
                str(sr),
                "-f",
                "wav",
                tmp_path,
            ]
            sec_subprocess.run_safe(
                cmd,
                allow_roots=SEC_CONFIG.allowed_binary_roots,
                timeout=SEC_CONFIG.subprocess_timeout,
                check=True,
            )
            y, sr_out = librosa.load(tmp_path, sr=sr, mono=mono)
            if y is None or len(y) == 0:
                raise RuntimeError(f"Failed to load audio from {path}")
            return np.asarray(y, dtype=np.float32), sr_out
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    raise RuntimeError(f"Unsupported audio backend: {backend}")
