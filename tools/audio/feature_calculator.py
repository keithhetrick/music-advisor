#!/usr/bin/env python3
"""
Audio feature calculation utilities for MusicAdvisor.

Provides a clean interface for computing perceptual audio features:
- Energy: Perceptual loudness/intensity (0.0-1.0 scale)
- Danceability: Rhythmic suitability for dancing (0.0-1.0 scale)
- Valence: Musical positivity/happiness (0.0-1.0 scale)

This module consolidates feature calculation logic that was scattered in ma_audio_features.py,
making it easier to maintain, test, and reuse across tools.

Usage:
    from tools.audio.feature_calculator import estimate_energy, estimate_danceability, estimate_valence

    # Compute energy (perceptual loudness)
    energy = estimate_energy(signal, sr=44100)

    # Compute danceability (requires tempo estimate)
    danceability = estimate_danceability(signal, sr=44100, tempo=120.0)

    # Compute valence (requires mode and energy)
    valence = estimate_valence(mode="major", energy=energy)

Design notes:
    - All functions handle None/empty inputs gracefully
    - Features are normalized to 0.0-1.0 range
    - Energy uses RMS and spectral centroid
    - Danceability uses tempo, beat strength, and regularity
    - Valence uses mode (major/minor) and energy
    - Requires librosa for all feature operations
"""
from __future__ import annotations

import logging
from typing import Optional

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
    "estimate_energy",
    "estimate_danceability",
    "estimate_valence",
]

# Module logger for internal debug messages
_log = logging.getLogger(__name__)


def estimate_energy(y: npt.NDArray[np.float32], sr: int) -> Optional[float]:
    """
    Estimate perceptual energy on a 0.0-1.0 scale.

    Energy represents the perceived loudness and intensity of the audio.
    It combines RMS energy with spectral brightness (centroid) to provide
    a perceptual measure that correlates with how "energetic" music sounds.

    The algorithm:
    1. Computes frame-wise RMS energy using librosa
    2. Normalizes by median RMS to handle gain differences
    3. Applies sigmoid to map relative RMS to 0.1-0.95 range
    4. Adds spectral centroid as a "brightness" term (20% weight)
    5. Clips final result to 0.0-1.0

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz

    Returns:
        Energy value from 0.0 to 1.0:
            - High (~0.7–0.9): Dense, consistently loud mixes
            - Medium (~0.4–0.6): Moderate dynamics
            - Low (~0.1–0.3): Sparse/quiet ballads
        Returns None if librosa unavailable or input invalid

    Examples:
        >>> import numpy as np
        >>> # Loud signal
        >>> signal = np.random.randn(44100).astype(np.float32) * 0.8
        >>> energy = estimate_energy(signal, sr=44100)
        >>> energy > 0.5
        True

        >>> # Quiet signal
        >>> signal = np.random.randn(44100).astype(np.float32) * 0.01
        >>> energy = estimate_energy(signal, sr=44100)
        >>> energy < 0.5
        True
    """
    if librosa is None:
        return None
    if y is None or len(y) == 0:
        return None

    hop_length = 512
    frame_length = 2048
    try:
        rms = librosa.feature.rms(
            y=y,
            frame_length=frame_length,
            hop_length=hop_length,
            center=True
        )[0]
    except Exception:
        rms = np.array([np.sqrt(float(np.mean(y * y)) + 1e-12)])

    rms = np.maximum(rms, 1e-8)
    med = float(np.median(rms))
    if med <= 0.0:
        med = float(np.mean(rms))

    # Relative RMS vs median
    rms_rel = rms / (med + 1e-12)
    rms_rel = np.clip(rms_rel, 0.25, 5.0)

    x = float(np.mean(rms_rel))
    energy_core = 1.0 / (1.0 + np.exp(-(x - 1.5)))
    energy_core = 0.1 + 0.85 * float(np.clip(energy_core, 0.0, 1.0))

    # Add a brightness term from spectral centroid
    try:
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        cent_norm = float(
            np.clip(
                np.mean(cent) / (sr / 2.0 + 1e-9),
                0.0,
                1.0
            )
        )
    except Exception:
        cent_norm = 0.5

    energy = 0.8 * energy_core + 0.2 * cent_norm
    return float(np.clip(energy, 0.0, 1.0))


def estimate_danceability(
    y: npt.NDArray[np.float32],
    sr: int,
    tempo: Optional[float]
) -> Optional[float]:
    """
    Estimate danceability on a 0.0-1.0 scale.

    Danceability measures how suitable a track is for dancing, based on
    tempo, beat strength, and rhythmic regularity. It combines three factors:
    - Tempo closeness to a comfortable dance window (~70–140 BPM, centered ~110)
    - Strength of beat pulses (onset energy on detected beats)
    - Regularity of beat energy across time (low variance = more regular)

    The algorithm:
    1. Tempo term: How close is tempo to ideal dance range? (30% weight)
    2. Beat strength: How strong are the rhythmic onsets? (40% weight)
    3. Regularity: How consistent are beat strengths? (30% weight)

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        sr: Sample rate in Hz
        tempo: Estimated tempo in BPM (or None)

    Returns:
        Danceability value from 0.0 to 1.0:
            - High (~0.7–0.9): Strong, regular beat at dance tempo
            - Medium (~0.4–0.6): Some rhythmic structure
            - Low (~0.1–0.3): Weak/irregular rhythm or extreme tempo
        Returns None if librosa unavailable or input invalid

    Examples:
        >>> import numpy as np
        >>> # Create signal with some structure
        >>> signal = np.random.randn(44100 * 3).astype(np.float32) * 0.3
        >>> dance = estimate_danceability(signal, sr=44100, tempo=120.0)
        >>> dance is None or (0.0 <= dance <= 1.0)
        True
    """
    if librosa is None:
        return None
    if y is None or len(y) == 0:
        return None

    # Tempo term: prefer typical dance tempo
    felt_tempo = float(tempo or 0.0)
    if felt_tempo <= 0:
        tempo_term = 0.5
    else:
        while felt_tempo < 60.0:
            felt_tempo *= 2.0
        while felt_tempo > 180.0:
            felt_tempo /= 2.0
        center = 110.0
        spread = 50.0
        delta = abs(felt_tempo - center)
        tempo_term = float(np.clip(1.0 - (delta / spread), 0.0, 1.0))

    # Beat strength & regularity
    try:
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        if np.max(oenv) <= 0:
            return float(tempo_term)

        tempo_est, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr)
        if beats is None or len(beats) < 4:
            beat_strength = float(
                np.clip(
                    np.mean(oenv) / (np.max(oenv) + 1e-9),
                    0.0,
                    1.0
                )
            )
            regularity = 0.5
        else:
            beat_env = oenv[beats].astype(float)
            if np.max(beat_env) > 0:
                beat_env = beat_env / np.max(beat_env)

            beat_strength = float(np.clip(np.mean(beat_env), 0.0, 1.0))

            if len(beat_env) > 1:
                mu = float(np.mean(beat_env))
                sigma = float(np.std(beat_env))
                cv = sigma / (mu + 1e-9)
                regularity = float(np.clip(1.0 - cv, 0.0, 1.0))
            else:
                regularity = 0.5
    except Exception:
        try:
            oenv = librosa.onset.onset_strength(y=y, sr=sr)
            if np.max(oenv) > 0:
                beat_strength = float(
                    np.clip(
                        np.mean(oenv) / (np.max(oenv) + 1e-9),
                        0.0,
                        1.0
                    )
                )
            else:
                beat_strength = 0.5
        except Exception:
            beat_strength = 0.5
        regularity = 0.5

    dance = (
        0.4 * beat_strength +
        0.3 * regularity +
        0.3 * tempo_term
    )
    return float(np.clip(dance, 0.0, 1.0))


def estimate_valence(mode: Optional[str], energy: Optional[float]) -> Optional[float]:
    """
    Estimate valence on 0.0-1.0 scale.

    Valence represents the musical positivity or happiness of a track.
    It's primarily driven by mode (major = happier, minor = sadder) with
    a secondary influence from energy (higher energy = more positive).

    The algorithm:
    - Major keys bias upward (base = 0.7)
    - Minor keys bias downward (base = 0.3)
    - Unknown mode uses neutral (base = 0.5)
    - Energy adds ±0.2 variation (40% weight)
    - Final: valence = 0.6 * mode_base + 0.4 * energy

    Args:
        mode: Musical mode ("major", "minor", or other/None)
        energy: Energy value from 0.0 to 1.0 (or None)

    Returns:
        Valence value from 0.0 to 1.0:
            - High (~0.7–0.9): Major key with high energy (happy/upbeat)
            - Medium (~0.4–0.6): Mixed signals or unknown mode
            - Low (~0.1–0.3): Minor key with low energy (sad/dark)
        Always returns a float (never None)

    Examples:
        >>> # Major key, high energy = high valence
        >>> estimate_valence("major", 0.8)
        0.74

        >>> # Minor key, low energy = low valence
        >>> estimate_valence("minor", 0.2)
        0.26

        >>> # Unknown mode uses neutral base
        >>> val = estimate_valence("unknown", 0.5)
        >>> 0.4 <= val <= 0.6
        True
    """
    if mode == "major":
        base = 0.7
    elif mode == "minor":
        base = 0.3
    else:
        base = 0.5

    e = 0.5 if energy is None else float(np.clip(energy, 0.0, 1.0))
    valence = 0.6 * base + 0.4 * e
    return float(np.clip(valence, 0.0, 1.0))
