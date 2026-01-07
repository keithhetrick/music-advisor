#!/usr/bin/env python3
"""
Loudness and LUFS (Loudness Units relative to Full Scale) analysis.

Provides integrated loudness measurement using pyloudnorm (ITU-R BS.1770-4 standard)
with fallback to RMS-based approximation.

Functions:
- estimate_lufs: Measure integrated LUFS of audio signal
- normalize_audio: Normalize audio to target LUFS level

References:
- ITU-R BS.1770-4: Algorithms to measure audio programme loudness
- EBU R 128: Loudness normalisation and permitted maximum level of audio signals
"""

import math
from typing import Optional, Tuple

import numpy as np

try:
    import pyloudnorm as pyln
except ImportError:
    pyln = None

__all__ = ["estimate_lufs", "normalize_audio"]


def estimate_lufs(y: np.ndarray, sr: int) -> Optional[float]:
    """
    Estimate integrated LUFS using pyloudnorm if available.
    Falls back to a simple RMS-based approximation if not.

    Args:
        y: Audio signal as numpy array (mono or stereo)
        sr: Sample rate in Hz

    Returns:
        Integrated LUFS value, or None if signal is empty/invalid

    Notes:
        - Uses pyloudnorm.Meter for ITU-R BS.1770-4 compliant measurement
        - Fallback approximation: LUFS ≈ 20*log10(RMS) - 0.691
        - Returns None for empty or invalid input
    """
    if y is None or len(y) == 0:
        return None

    if pyln is not None:
        try:
            meter = pyln.Meter(sr)
            return float(meter.integrated_loudness(y))
        except Exception:
            # Fall through to RMS approximation
            pass

    # Fallback: approximate LUFS from RMS
    rms = np.sqrt(np.mean(y * y) + 1e-12)
    lufs_approx = 20.0 * math.log10(rms + 1e-12) - 0.691
    return float(lufs_approx)


def normalize_audio(
    y: np.ndarray, sr: int, target_lufs: float = -14.0
) -> Tuple[np.ndarray, float, Optional[float]]:
    """
    Normalize audio to target LUFS (in-memory).

    Args:
        y: Input audio signal as numpy array
        sr: Sample rate in Hz
        target_lufs: Target integrated loudness in LUFS (default: -14.0 per EBU R 128)

    Returns:
        Tuple of (normalized_audio, gain_db, normalized_lufs):
        - normalized_audio: Gain-adjusted audio signal
        - gain_db: Applied gain in dB
        - normalized_lufs: Measured LUFS after normalization (may differ from target)

    Notes:
        - If LUFS cannot be computed, returns original signal with 0 dB gain
        - Gain is clamped to [-12, +12] dB to prevent excessive adjustments
        - Target of -14 LUFS matches streaming platform standards (Spotify, YouTube, etc.)
    """
    raw_lufs = estimate_lufs(y, sr)
    if raw_lufs is None:
        return y, 0.0, None

    gain_db = target_lufs - raw_lufs
    # Clamp extreme gains to avoid excessive boosts/cuts
    gain_db = float(np.clip(gain_db, -12.0, 12.0))
    gain = 10.0 ** (gain_db / 20.0)
    y_norm = y * gain
    norm_lufs = estimate_lufs(y_norm, sr)
    return y_norm, gain_db, norm_lufs
