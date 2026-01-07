#!/usr/bin/env python3
"""
Audio loading utilities for MusicAdvisor.

Provides a clean interface for loading and preprocessing audio files with:
- Multiple format support (wav, mp3, flac, etc.)
- Automatic mono conversion
- Sample rate resampling
- Duration validation
- Best-effort format detection

This module consolidates audio I/O logic that was scattered across tools,
making it easier to maintain and test. It wraps the underlying audio_loader_adapter
from ma_audio_engine while adding convenience functions for common workflows.

Usage:
    from tools.audio.audio_loader import load_audio, probe_audio_duration

    # Load audio file as mono at target sample rate
    signal, sr = load_audio("song.mp3", sr=44100)

    # Check duration before loading (fast)
    duration = probe_audio_duration("song.mp3")
    if duration and duration > 600:
        print("File too long!")

Design notes:
    - Re-exports load_audio_mono from adapters (already handles librosa + ffmpeg fallback)
    - Adds probe_audio_duration for pre-flight duration checks
    - Handles both soundfile and ffprobe backends for probing
    - All I/O errors propagate as RuntimeError with context
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt

# Import the core loader from adapters (handles librosa + ffmpeg fallback)
from ma_audio_engine.adapters import load_audio_mono

# Try to import soundfile for fast duration probing
try:
    import soundfile as sf
except ImportError:
    sf = None  # type: ignore

__all__ = [
    "load_audio",
    "load_audio_mono",
    "probe_audio_duration",
]


def load_audio(
    path: str,
    sr: int = 44100,
) -> Tuple[npt.NDArray[np.float32], int]:
    """
    Load audio file as mono signal at specified sample rate.

    This is a convenience wrapper around load_audio_mono that provides
    a simpler interface for the most common use case.

    Args:
        path: Path to audio file (supports wav, mp3, flac, ogg, etc.)
        sr: Target sample rate for resampling (default: 44100 Hz)

    Returns:
        Tuple of (signal, sample_rate):
            - signal: Mono audio as float32 numpy array, normalized to [-1, 1]
            - sample_rate: Actual sample rate (should match `sr` parameter)

    Raises:
        RuntimeError: If file cannot be loaded or decoded

    Examples:
        >>> signal, sr = load_audio("song.mp3", sr=44100)
        >>> print(f"Loaded {len(signal)} samples at {sr} Hz")
        Loaded 2646000 samples at 44100 Hz

        >>> duration = len(signal) / sr
        >>> print(f"Duration: {duration:.2f} seconds")
        Duration: 60.00 seconds
    """
    return load_audio_mono(path, sr=sr)


def probe_audio_duration(path: str) -> Optional[float]:
    """
    Probe audio file duration without decoding the entire file.

    This is a fast, best-effort duration check useful for validating files
    before loading (e.g., rejecting oversized inputs). It tries multiple
    strategies in order of preference:

    1. soundfile (if available) - fastest, works for wav/flac/ogg
    2. ffprobe (if available) - slower but works for mp3/m4a/etc.

    Args:
        path: Path to audio file

    Returns:
        Duration in seconds (float) or None if probe fails

    Notes:
        - Returns None if no probe method is available or if probe fails
        - Does NOT decode audio, only reads file metadata
        - May return None even if file is valid (if all probes fail)
        - Use this for quick rejection of oversized files before decode

    Examples:
        >>> duration = probe_audio_duration("song.mp3")
        >>> if duration and duration > 600:
        ...     print("File too long (>10 minutes)")
        File too long (>10 minutes)

        >>> # Fast pre-flight check before expensive processing
        >>> path = "input.wav"
        >>> dur = probe_audio_duration(path)
        >>> if dur is None:
        ...     print("Warning: Could not probe duration")
        ... elif dur > 900:
        ...     raise ValueError("File exceeds 15 minute limit")
        ... else:
        ...     signal, sr = load_audio(path)
    """
    # Check if any probe method is available
    probe_capable = bool(sf) or bool(shutil.which("ffprobe"))
    if not probe_capable:
        return None

    # Try soundfile first (fastest for supported formats)
    if sf:
        try:
            info = sf.info(path)
            dur = float(info.duration)
            if math.isfinite(dur) and dur > 0:
                return dur
        except Exception:
            # Fall through to ffprobe
            pass

    # Try ffprobe as fallback (works for more formats)
    if shutil.which("ffprobe"):
        try:
            completed = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,  # Prevent hanging on problematic files
            )
            out = completed.stdout.decode().strip()
            if out:
                dur = float(out)
                if math.isfinite(dur) and dur > 0:
                    return dur
        except Exception:
            # Probe failed, return None
            pass

    # All probe attempts failed
    return None
