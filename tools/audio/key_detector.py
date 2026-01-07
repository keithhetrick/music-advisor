#!/usr/bin/env python3
"""
Musical key and mode detection utilities for MusicAdvisor.

Provides a clean interface for detecting musical keys and modes:
- Key detection: Identify root pitch class (C, C#, D, etc.)
- Mode detection: Identify major vs minor tonality
- Confidence scoring: Assess key detection certainty

This module consolidates key/mode detection logic that was scattered in ma_audio_features.py,
making it easier to maintain, test, and reuse across tools.

Usage:
    from tools.audio.key_detector import estimate_mode_and_key, key_confidence_label

    # Detect key and mode from audio
    key, mode = estimate_mode_and_key(signal, sr=44100)
    # Returns: ("C", "major"), ("A", "minor"), etc.

    # Get confidence label
    confidence = key_confidence_label(key)
    # Returns: "med" if key detected, "low" if None

Design notes:
    - All functions handle None/empty inputs gracefully
    - Key detection uses chroma CQT analysis
    - Mode inference based on chroma spread (crude heuristic)
    - Requires librosa for all operations
    - Returns None for both key and mode on failure
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt

# Lazy import librosa (optional dependency)
try:
    import librosa
    import librosa.feature
except ImportError:
    librosa = None  # type: ignore

__all__ = [
    "estimate_mode_and_key",
    "key_confidence_label",
    "normalize_key_confidence",
    "NOTE_NAMES_SHARP",
]

# Module logger for internal debug messages
_log = logging.getLogger(__name__)

# Pitch class names using sharp notation
NOTE_NAMES_SHARP = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]


def estimate_mode_and_key(
    y: npt.NDArray[np.float32],
    sr: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    Estimate musical key and mode from audio signal.

    This is a crude key estimation using chroma feature analysis:
    1. Compute chroma CQT (constant-Q transform chromagram)
    2. Average across time to get mean chroma vector
    3. Select pitch class with highest energy as root
    4. Infer mode from chroma spread (major = higher variance)

    Note: This is a simple heuristic and not a sophisticated key detector.
    For production use, consider external tools like Essentia's KeyExtractor.

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz

    Returns:
        Tuple of (key_root, mode):
            - key_root: Root pitch class ("C", "C#", "D", etc.) or None
            - mode: Musical mode ("major" or "minor") or None
        Returns (None, None) if librosa unavailable or estimation fails

    Examples:
        >>> import numpy as np
        >>> # Create a signal (random for demo - real music gives better results)
        >>> signal = np.random.randn(44100 * 5).astype(np.float32) * 0.3
        >>> key, mode = estimate_mode_and_key(signal, sr=44100)
        >>> key in NOTE_NAMES_SHARP or key is None
        True
        >>> mode in ("major", "minor") or mode is None
        True
    """
    if librosa is None:
        return None, None
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        root_index = int(np.argmax(chroma_mean))
        key_root = NOTE_NAMES_SHARP[root_index]

        # Crude mode inference: higher spread = major, lower = minor
        spread = float(np.std(chroma_mean))
        if spread > 0.05:
            mode = "major"
        else:
            mode = "minor"

        return key_root, mode
    except Exception as e:
        _log.debug(f"mode/key estimation failed: {e}")
        return None, None


def key_confidence_label(key_root: Optional[str]) -> str:
    """
    Generate a confidence label for key detection.

    This is a simple heuristic:
    - "med" if a key was detected (key_root is not None)
    - "low" if no key was detected (key_root is None)

    Args:
        key_root: Detected key root ("C", "D", etc.) or None

    Returns:
        Confidence label: "med" or "low"

    Examples:
        >>> key_confidence_label("C")
        'med'
        >>> key_confidence_label(None)
        'low'
        >>> key_confidence_label("F#")
        'med'
    """
    return "med" if key_root else "low"


def normalize_key_confidence(raw_score: Optional[float]) -> Optional[float]:
    """
    Normalize/clamp key confidence score to 0.0-1.0 range.

    This function ensures external key confidence scores are in the
    standard 0.0-1.0 range by clamping values.

    Args:
        raw_score: Raw confidence/strength score (any float) or None

    Returns:
        Normalized score from 0.0 to 1.0, or None if input is None

    Examples:
        >>> normalize_key_confidence(0.5)
        0.5
        >>> normalize_key_confidence(1.5)  # Clamps to 1.0
        1.0
        >>> normalize_key_confidence(-0.2)  # Clamps to 0.0
        0.0
        >>> normalize_key_confidence(None)
        >>> # Returns None
    """
    if raw_score is None:
        return None
    try:
        return float(np.clip(float(raw_score), 0.0, 1.0))
    except Exception:
        return None
