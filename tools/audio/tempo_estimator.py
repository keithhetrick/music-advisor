#!/usr/bin/env python3
"""
Tempo/BPM estimation utilities for MusicAdvisor.

Provides a clean interface for tempo detection and confidence calculation:
- Beat tracking and tempo estimation using librosa
- Tempo folding to preferred BPM ranges
- Confidence scoring based on onset strength, beat count, and tempogram analysis
- Fallback strategies for robust estimation

This module consolidates tempo estimation logic that was scattered in ma_audio_features.py,
making it easier to maintain, test, and reuse across tools.

Usage:
    from tools.audio.tempo_estimator import estimate_tempo_with_folding, compute_tempo_confidence

    # Estimate tempo with automatic folding to comfortable range (60-180 BPM)
    primary, half, double, reason = estimate_tempo_with_folding(signal, sr=44100)

    # Compute confidence score for tempo estimate
    score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=primary)

Design notes:
    - All functions handle None/empty inputs gracefully
    - Tempo folding prefers 60-180 BPM range with bias toward 110 BPM
    - Confidence scoring combines onset contrast, beat count, and tempogram peaks
    - Requires librosa for all tempo operations
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt

# Lazy import librosa (optional dependency)
try:
    import librosa
    import librosa.beat
    import librosa.feature
    import librosa.onset
except ImportError:
    librosa = None  # type: ignore

__all__ = [
    "robust_tempo",
    "estimate_tempo_with_folding",
    "select_tempo_with_folding",
    "compute_tempo_confidence",
]

# Module logger for internal debug messages
_log = logging.getLogger(__name__)


def _pad_short_signal(
    y: Optional[npt.NDArray[np.float32]],
    *,
    min_len: int = 2048,
    label: str = "short_signal"
) -> Optional[npt.NDArray[np.float32]]:
    """
    Pad short signals to avoid librosa FFT warnings on tiny inputs.

    Args:
        y: Input audio signal (mono, float32)
        min_len: Minimum length threshold for padding
        label: Debug label for logging

    Returns:
        Padded array (or original if already sufficient)
    """
    if y is None:
        return y
    if len(y) >= min_len:
        return y
    pad = min_len - len(y)
    _log.debug(f"{label}_pad:{len(y)}->{min_len}")
    return np.pad(y, (0, pad), mode="constant")


def _fold_tempo_to_window(bpm: float, low: float = 60.0, high: float = 180.0) -> float:
    """
    Fold a tempo value into the target BPM window by repeated doubling/halving.

    Args:
        bpm: Input tempo in BPM
        low: Lower bound of target window (default: 60 BPM)
        high: Upper bound of target window (default: 180 BPM)

    Returns:
        Folded tempo within [low, high] range

    Examples:
        >>> _fold_tempo_to_window(40.0)  # Too slow, double it
        80.0
        >>> _fold_tempo_to_window(200.0)  # Too fast, halve it
        100.0
        >>> _fold_tempo_to_window(120.0)  # Already in range
        120.0
    """
    folded = float(bpm)
    steps = 0
    while folded < low and steps < 6:
        folded *= 2.0
        steps += 1
    while folded > high and steps < 6:
        folded /= 2.0
        steps += 1
    return folded


def robust_tempo(y: npt.NDArray[np.float32], sr: int) -> Optional[float]:
    """
    Tempo estimate using librosa.beat.beat_track with robust error handling.

    This is the primary tempo estimation function, using librosa's beat tracker
    to detect tempo. It handles array/scalar return values and provides
    graceful fallback on errors.

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz

    Returns:
        Tempo in BPM (float) or None if estimation fails

    Examples:
        >>> import numpy as np
        >>> signal = np.random.randn(44100).astype(np.float32) * 0.3
        >>> tempo = robust_tempo(signal, sr=44100)
        >>> tempo is None or 30.0 <= tempo <= 300.0
        True
    """
    if librosa is None:
        return None
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, (list, np.ndarray)):
            tempo = float(tempo[0])
        return float(tempo)
    except Exception as e:
        _log.debug(f"tempo estimation failed: {e}")
        return None


def select_tempo_with_folding(
    base_tempo: Optional[float]
) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """
    Select best tempo variant (base/half/double) by folding into 60-180 BPM window.

    This function tests three variants of the input tempo (base, half, double) and
    selects the one that folds closest to 110 BPM within the 60-180 BPM range.
    This handles cases where beat tracking detects half-time or double-time.

    Args:
        base_tempo: Input tempo in BPM (or None)

    Returns:
        Tuple of (primary_tempo, half_tempo, double_tempo, reason):
            - primary_tempo: Selected best tempo after folding
            - half_tempo: Half of base tempo
            - double_tempo: Double of base tempo
            - reason: Debug string explaining selection

    Examples:
        >>> select_tempo_with_folding(80.0)
        (80.0, 40.0, 160.0, 'base_selected_folded_to_80.0_bpm')

        >>> select_tempo_with_folding(50.0)  # Prefers 100 (double) over 50
        (100.0, 50.0, 200.0, 'double_selected_folded_to_100.0_bpm')

        >>> select_tempo_with_folding(None)
        (None, None, None, 'no_tempo')
    """
    if base_tempo is None or base_tempo <= 0:
        return None, None, None, "no_tempo"

    candidates = [
        ("base", float(base_tempo)),
        ("half", float(base_tempo) / 2.0),
        ("double", float(base_tempo) * 2.0),
    ]
    best = None
    for label, bpm in candidates:
        if bpm <= 0:
            continue
        folded = _fold_tempo_to_window(bpm)
        # Prefer tempos that fold into the comfortable 60–180 window and near 110 BPM
        delta = abs(folded - 110.0)
        score = delta
        if best is None or score < best[0]:
            best = (score, label, bpm, folded)

    if best is None:
        return None, None, None, "no_valid_tempo"

    _, label, bpm, folded = best
    reason = f"{label}_selected_folded_to_{folded:.1f}_bpm"
    primary = folded
    alt_half = candidates[1][1]
    alt_double = candidates[2][1]
    return primary, alt_half, alt_double, reason


def estimate_tempo_with_folding(
    y: npt.NDArray[np.float32],
    sr: int
) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """
    Estimate tempo with automatic folding to comfortable BPM range (60-180).

    This is the main entry point for tempo estimation. It:
    1. Pads short signals to avoid FFT warnings
    2. Attempts robust beat tracking (robust_tempo)
    3. Falls back to librosa.beat.tempo with median aggregation
    4. Selects best variant (base/half/double) via folding

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz

    Returns:
        Tuple of (primary_tempo, half_tempo, double_tempo, reason):
            - primary_tempo: Best tempo estimate after folding
            - half_tempo: Half-time variant
            - double_tempo: Double-time variant
            - reason: Debug string explaining estimation path

    Examples:
        >>> import numpy as np
        >>> # Create 120 BPM click track (simplified example)
        >>> sr = 44100
        >>> duration = 10  # seconds
        >>> signal = np.random.randn(sr * duration).astype(np.float32) * 0.1
        >>> primary, half, double, reason = estimate_tempo_with_folding(signal, sr)
        >>> primary is None or 40.0 <= primary <= 200.0
        True
    """
    if librosa is None or y is None or len(y) == 0:
        return None, None, None, "librosa_unavailable_or_empty_audio"

    y = _pad_short_signal(y, min_len=1024, label="tempo_fold")
    base = robust_tempo(y, sr)

    if base is None:
        try:
            oenv = librosa.onset.onset_strength(y=y, sr=sr)
            temp = librosa.beat.tempo(onset_envelope=oenv, sr=sr, aggregate=np.median)
            if isinstance(temp, (list, np.ndarray)):
                base = float(temp[0])
            else:
                base = float(temp)
        except Exception as e:
            _log.debug(f"fallback tempo estimation failed: {e}")
            base = None

    return select_tempo_with_folding(base)


def compute_tempo_confidence(
    y: npt.NDArray[np.float32],
    sr: int,
    tempo_primary: Optional[float]
) -> Tuple[float, str]:
    """
    Estimate tempo confidence using onset strength contrast, beat count, and tempogram peak.

    This function computes a confidence score (0.0-1.0) for a tempo estimate by analyzing:
    - Onset strength contrast: How pronounced are the rhythmic onsets?
    - Beat count: How many beats were detected?
    - Tempogram peak: How strong is the tempogram peak near the estimated tempo?

    The score is a weighted combination:
        score = 0.4 * contrast_norm + 0.3 * beat_norm + 0.3 * peak_ratio

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz
        tempo_primary: Estimated tempo in BPM (or None)

    Returns:
        Tuple of (score, label):
            - score: Confidence score from 0.0 to 1.0
            - label: One of "low" (<0.33), "med" (0.33-0.66), or "high" (>=0.66)

    Examples:
        >>> import numpy as np
        >>> signal = np.random.randn(44100).astype(np.float32) * 0.3
        >>> score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=120.0)
        >>> 0.0 <= score <= 1.0
        True
        >>> label in ("low", "med", "high")
        True
    """
    if tempo_primary is None or tempo_primary <= 0 or librosa is None or y is None or len(y) == 0:
        return 0.2, "low"

    y = _pad_short_signal(y, min_len=1024, label="tempo_conf")

    try:
        hop_length = 512
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        if oenv.size == 0:
            return 0.2, "low"

        # Onset strength contrast
        contrast = float(np.max(oenv) / (np.mean(oenv) + 1e-9))
        contrast_norm = float(np.clip((contrast - 1.0) / 4.0, 0.0, 1.0))

        # Beat count
        tempo_est, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop_length)
        beat_count = len(beats) if beats is not None else 0
        beat_norm = float(np.clip(beat_count / 32.0, 0.0, 1.0))

        # Tempogram peak near estimated tempo
        tempogram = librosa.feature.tempogram(onset_envelope=oenv, sr=sr, hop_length=hop_length)
        tempos = librosa.tempo_frequencies(tempogram.shape[0], sr=sr, hop_length=hop_length)
        idx = int(np.argmin(np.abs(tempos - tempo_primary)))
        peak_near = float(tempogram[idx].max()) if tempogram.shape[1] > 0 else 0.0
        peak_global = float(tempogram.max()) if tempogram.size > 0 else 0.0
        peak_ratio = float(peak_near / (peak_global + 1e-9)) if peak_global > 0 else 0.0

        # Weighted combination
        score = float(np.clip(0.4 * contrast_norm + 0.3 * beat_norm + 0.3 * peak_ratio, 0.0, 1.0))

        if score >= 0.66:
            label = "high"
        elif score >= 0.33:
            label = "med"
        else:
            label = "low"

        return score, label
    except Exception:
        return 0.2, "low"
