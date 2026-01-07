#!/usr/bin/env python3
"""
QA (Quality Assurance) checker for audio signals.

Extracted from ma_audio_features.py to provide standalone quality checking
for audio processing pipelines. This module detects common audio issues:
- Clipping (signal peaks near digital maximum)
- Excessive silence
- Low-level signals (too quiet)

Usage:
    from tools.audio.qa_checker import compute_qa_metrics, determine_qa_status

    # Compute QA metrics for an audio signal
    qa_metrics = compute_qa_metrics(
        audio_signal,
        clip_peak_threshold=0.999,
        silence_ratio_threshold=0.9,
        low_level_dbfs_threshold=-40.0
    )

    # Determine overall QA status
    status, gate = determine_qa_status(qa_metrics)
"""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np
import numpy.typing as npt

__all__ = [
    "compute_qa_metrics",
    "determine_qa_status",
    "validate_qa_strict",
]


def compute_qa_metrics(
    y: npt.NDArray[np.float32],
    clip_peak_threshold: float = 0.999,
    silence_ratio_threshold: float = 0.9,
    low_level_dbfs_threshold: float = -40.0,
) -> Dict[str, Any]:
    """
    Compute quality assurance metrics for an audio signal.

    Args:
        y: Audio signal as numpy array (mono, float32, normalized to [-1, 1])
        clip_peak_threshold: Peak threshold for clipping detection (default: 0.999)
        silence_ratio_threshold: Ratio threshold for silence detection (default: 0.9)
        low_level_dbfs_threshold: dBFS threshold for low-level detection (default: -40.0)

    Returns:
        Dictionary containing:
            - peak_dbfs: Peak level in dBFS
            - rms_dbfs: RMS level in dBFS
            - clipping: Boolean indicating if clipping detected
            - silence_ratio: Ratio of samples below noise floor
            - clip_peak_threshold: Threshold used for clipping detection
            - silence_ratio_threshold: Threshold used for silence detection
            - low_level_dbfs_threshold: Threshold used for low-level detection

    Examples:
        >>> import numpy as np
        >>> signal = np.random.randn(44100).astype(np.float32) * 0.1
        >>> qa = compute_qa_metrics(signal)
        >>> qa['clipping']
        False
        >>> qa['peak_dbfs'] < 0
        True
    """
    if y is None or len(y) == 0:
        # Return empty metrics for missing audio
        return {
            "peak_dbfs": -float("inf"),
            "rms_dbfs": -float("inf"),
            "clipping": False,
            "silence_ratio": 1.0,
            "clip_peak_threshold": clip_peak_threshold,
            "silence_ratio_threshold": silence_ratio_threshold,
            "low_level_dbfs_threshold": low_level_dbfs_threshold,
        }

    # Compute peak and RMS levels
    peak = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y * y) + 1e-12))

    # Convert to dBFS (decibels relative to full scale)
    peak_dbfs = float(20.0 * math.log10(peak + 1e-12))
    rms_dbfs = float(20.0 * math.log10(rms + 1e-12))

    # Detect clipping (peak near digital maximum)
    clipping = peak >= clip_peak_threshold

    # Compute silence ratio (proportion of samples near zero)
    silence_ratio = float(np.mean(np.abs(y) < 1e-4))

    return {
        "peak_dbfs": peak_dbfs,
        "rms_dbfs": rms_dbfs,
        "clipping": clipping,
        "silence_ratio": silence_ratio,
        "clip_peak_threshold": clip_peak_threshold,
        "silence_ratio_threshold": silence_ratio_threshold,
        "low_level_dbfs_threshold": low_level_dbfs_threshold,
    }


def determine_qa_status(
    qa_metrics: Dict[str, Any],
    fail_on_clipping_dbfs: float | None = None,
) -> Tuple[str, str]:
    """
    Determine overall QA status based on computed metrics.

    Args:
        qa_metrics: Dictionary from compute_qa_metrics()
        fail_on_clipping_dbfs: Optional dBFS threshold to raise error on clipping

    Returns:
        Tuple of (status, gate):
            - status: One of "ok", "warn_clipping", "warn_silence", "warn_low_level"
            - gate: One of "pass" or the warning status

    Raises:
        RuntimeError: If fail_on_clipping_dbfs is set and peak exceeds threshold

    Examples:
        >>> metrics = {"clipping": False, "silence_ratio": 0.1, "rms_dbfs": -20.0}
        >>> status, gate = determine_qa_status(metrics)
        >>> status
        'ok'
        >>> gate
        'pass'
    """
    # Default to "ok" status
    qa_status = "ok"

    # Check for clipping
    if qa_metrics.get("clipping"):
        qa_status = "warn_clipping"
        if fail_on_clipping_dbfs is not None:
            peak_dbfs = qa_metrics.get("peak_dbfs", 0.0)
            if peak_dbfs >= fail_on_clipping_dbfs:
                raise RuntimeError(
                    f"clipping error - peak_dbfs={peak_dbfs:.2f} "
                    f"exceeds fail_on_clipping_dbfs={fail_on_clipping_dbfs}"
                )

    # Check for excessive silence
    elif qa_metrics.get("silence_ratio", 0.0) > qa_metrics.get("silence_ratio_threshold", 0.9):
        qa_status = "warn_silence"

    # Check for low-level signal
    elif qa_metrics.get("rms_dbfs", 0.0) < qa_metrics.get("low_level_dbfs_threshold", -40.0):
        qa_status = "warn_low_level"

    # Gate is "pass" for ok, otherwise the warning status
    qa_gate = "pass" if qa_status == "ok" else qa_status

    return qa_status, qa_gate


def validate_qa_strict(
    qa_metrics: Dict[str, Any],
    qa_status: str,
) -> None:
    """
    Validate QA metrics in strict mode.

    Args:
        qa_metrics: Dictionary from compute_qa_metrics()
        qa_status: Status string from determine_qa_status()

    Raises:
        RuntimeError: If qa_status is not "ok" in strict mode

    Examples:
        >>> metrics = {"peak_dbfs": -1.0, "rms_dbfs": -20.0, "silence_ratio": 0.1}
        >>> validate_qa_strict(metrics, "ok")  # No error
        >>> validate_qa_strict(metrics, "warn_clipping")  # Raises RuntimeError
        Traceback (most recent call last):
        ...
        RuntimeError: strict QA failed (warn_clipping) ...
    """
    if qa_status != "ok":
        peak_dbfs = qa_metrics.get("peak_dbfs", 0.0)
        rms_dbfs = qa_metrics.get("rms_dbfs", 0.0)
        silence_ratio = qa_metrics.get("silence_ratio", 0.0)
        raise RuntimeError(
            f"strict QA failed ({qa_status}) "
            f"peak_dbfs={peak_dbfs:.2f} rms_dbfs={rms_dbfs:.2f} "
            f"silence_ratio={silence_ratio:.3f}"
        )
