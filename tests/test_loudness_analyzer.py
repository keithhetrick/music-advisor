#!/usr/bin/env python3
"""
Unit tests for loudness_analyzer module.

Tests LUFS measurement and audio normalization with synthetic signals.
"""

import math
import sys
from pathlib import Path

import numpy as np

# Skip pytest conftest to avoid circular imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audio.loudness_analyzer import estimate_lufs, normalize_audio

try:
    import pytest
except ImportError:
    pytest = None


class TestEstimateLufs:
    """Test LUFS estimation."""

    def test_silence_returns_very_low_lufs(self):
        """Silence should return very low LUFS value."""
        sr = 44100
        duration = 1.0
        y = np.zeros(int(sr * duration))
        lufs = estimate_lufs(y, sr)
        # Silence will have very low LUFS (< -100 dB)
        assert lufs is not None
        assert lufs < -100.0

    def test_empty_signal_returns_none(self):
        """Empty signal should return None."""
        sr = 44100
        y = np.array([])
        lufs = estimate_lufs(y, sr)
        assert lufs is None

    def test_none_signal_returns_none(self):
        """None signal should return None."""
        sr = 44100
        lufs = estimate_lufs(None, sr)
        assert lufs is None

    def test_sine_wave_lufs(self):
        """Test LUFS measurement on a known sine wave."""
        sr = 44100
        duration = 1.0
        freq = 1000.0  # 1 kHz
        amplitude = 0.5  # -6 dBFS peak

        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = amplitude * np.sin(2 * np.pi * freq * t)

        lufs = estimate_lufs(y, sr)
        assert lufs is not None
        # For a sine wave with amplitude 0.5:
        # RMS = amplitude / sqrt(2) ≈ 0.354
        # Expected LUFS ≈ 20*log10(0.354) - 0.691 ≈ -9.7 - 0.691 ≈ -10.4
        # Allow some tolerance for different measurement methods
        assert -15.0 < lufs < -5.0

    def test_full_scale_sine_lufs(self):
        """Test LUFS measurement on full-scale sine wave."""
        sr = 44100
        duration = 1.0
        freq = 1000.0
        amplitude = 1.0  # 0 dBFS peak

        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = amplitude * np.sin(2 * np.pi * freq * t)

        lufs = estimate_lufs(y, sr)
        assert lufs is not None
        # Full-scale sine: RMS = 1/sqrt(2) ≈ 0.707
        # Expected LUFS ≈ 20*log10(0.707) - 0.691 ≈ -3.0 - 0.691 ≈ -3.7
        assert -8.0 < lufs < 0.0

    def test_short_signal(self):
        """Test LUFS measurement on very short signal."""
        sr = 44100
        duration = 0.1  # 100ms
        y = np.random.randn(int(sr * duration)) * 0.1

        lufs = estimate_lufs(y, sr)
        # Should still return a value, even if less accurate
        assert lufs is not None
        assert isinstance(lufs, float)


class TestNormalizeAudio:
    """Test audio normalization to target LUFS."""

    def test_normalize_to_target_lufs(self):
        """Test normalization adjusts signal to target LUFS."""
        sr = 44100
        duration = 1.0
        target_lufs = -14.0

        # Create a quiet signal
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = 0.1 * np.sin(2 * np.pi * 1000 * t)

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr, target_lufs)

        # Gain should be positive (signal was boosted)
        assert gain_db > 0

        # Normalized LUFS should be close to target
        assert norm_lufs is not None
        assert abs(norm_lufs - target_lufs) < 2.0  # Within 2 dB tolerance

    def test_normalize_preserves_shape(self):
        """Test that normalization preserves signal shape (only applies gain)."""
        sr = 44100
        duration = 1.0
        y = np.random.randn(int(sr * duration)) * 0.3

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr, target_lufs=-14.0)

        # Shape should be preserved
        assert y_norm.shape == y.shape

        # Verify gain relationship
        gain_linear = 10.0 ** (gain_db / 20.0)
        np.testing.assert_allclose(y_norm, y * gain_linear, rtol=1e-5)

    def test_normalize_empty_signal(self):
        """Test normalization of empty signal returns unchanged."""
        sr = 44100
        y = np.array([])

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr)

        assert len(y_norm) == 0
        assert gain_db == 0.0
        assert norm_lufs is None

    def test_normalize_gain_clamping(self):
        """Test that extreme gains are clamped to ±12 dB."""
        sr = 44100
        duration = 1.0

        # Create very quiet signal that would require huge boost
        y = 0.001 * np.sin(2 * np.pi * 1000 * np.linspace(0, duration, int(sr * duration), endpoint=False))

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr, target_lufs=-14.0)

        # Gain should be clamped to max +12 dB
        assert -12.0 <= gain_db <= 12.0

    def test_normalize_loud_signal_reduces_level(self):
        """Test that loud signal is attenuated."""
        sr = 44100
        duration = 1.0
        target_lufs = -14.0

        # Create a loud signal
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = 0.8 * np.sin(2 * np.pi * 1000 * t)

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr, target_lufs)

        # Gain should be negative (signal was attenuated)
        assert gain_db < 0

        # Normalized signal should be quieter
        assert np.abs(y_norm).max() < np.abs(y).max()

    def test_normalize_custom_target(self):
        """Test normalization to custom target LUFS."""
        sr = 44100
        duration = 1.0
        custom_target = -20.0  # Quieter target

        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = 0.5 * np.sin(2 * np.pi * 1000 * t)

        y_norm, gain_db, norm_lufs = normalize_audio(y, sr, target_lufs=custom_target)

        # Should normalize to custom target
        assert norm_lufs is not None
        assert abs(norm_lufs - custom_target) < 2.0


if __name__ == "__main__":
    if pytest:
        pytest.main([__file__, "-v", "--no-cov"])
    else:
        # Simple test runner
        print("Running tests without pytest...")
        test_lufs = TestEstimateLufs()
        test_norm = TestNormalizeAudio()

        tests = [
            (test_lufs.test_silence_returns_very_low_lufs, "silence_returns_very_low_lufs"),
            (test_lufs.test_empty_signal_returns_none, "empty_signal_returns_none"),
            (test_lufs.test_none_signal_returns_none, "none_signal_returns_none"),
            (test_lufs.test_sine_wave_lufs, "sine_wave_lufs"),
            (test_lufs.test_full_scale_sine_lufs, "full_scale_sine_lufs"),
            (test_lufs.test_short_signal, "short_signal"),
            (test_norm.test_normalize_to_target_lufs, "normalize_to_target_lufs"),
            (test_norm.test_normalize_preserves_shape, "normalize_preserves_shape"),
            (test_norm.test_normalize_empty_signal, "normalize_empty_signal"),
            (test_norm.test_normalize_gain_clamping, "normalize_gain_clamping"),
            (test_norm.test_normalize_loud_signal_reduces_level, "normalize_loud_signal_reduces_level"),
            (test_norm.test_normalize_custom_target, "normalize_custom_target"),
        ]

        passed = 0
        failed = 0
        for test_fn, name in tests:
            try:
                test_fn()
                print(f"✓ {name}")
                passed += 1
            except Exception as e:
                print(f"✗ {name}: {e}")
                failed += 1

        print(f"\n{passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)
