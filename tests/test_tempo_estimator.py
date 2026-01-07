#!/usr/bin/env python3
"""
Unit tests for tools/audio/tempo_estimator.py

Tests the tempo/BPM estimation functions for audio signal analysis.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.audio.tempo_estimator import (
    compute_tempo_confidence,
    estimate_tempo_with_folding,
    robust_tempo,
    select_tempo_with_folding,
)


class TestRobustTempo:
    """Tests for robust_tempo function."""

    def test_normal_signal(self):
        """Test tempo estimation for a normal audio signal."""
        # Create a signal with some rhythmic structure (not a perfect test, but checks basic functionality)
        sr = 44100
        duration = 5  # seconds
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        tempo = robust_tempo(signal, sr)

        # Should return a tempo value (may not be accurate for random noise)
        assert tempo is None or (30.0 <= tempo <= 300.0)

    def test_empty_signal(self):
        """Test handling of empty signal."""
        signal = np.array([], dtype=np.float32)

        tempo = robust_tempo(signal, sr=44100)

        # Should handle empty input gracefully
        assert tempo is None or isinstance(tempo, float)

    def test_very_short_signal(self):
        """Test handling of very short signal."""
        signal = np.random.randn(100).astype(np.float32) * 0.3

        tempo = robust_tempo(signal, sr=44100)

        # Should handle short input gracefully
        assert tempo is None or isinstance(tempo, float)


class TestSelectTempoWithFolding:
    """Tests for select_tempo_with_folding function."""

    def test_normal_tempo(self):
        """Test selection with a normal tempo value."""
        primary, half, double, reason = select_tempo_with_folding(120.0)

        assert primary == 120.0
        assert half == 60.0
        assert double == 240.0
        assert "base_selected" in reason

    def test_slow_tempo_doubles(self):
        """Test that slow tempos prefer the doubled variant."""
        primary, half, double, reason = select_tempo_with_folding(50.0)

        # Should prefer 100 BPM (which could be base folded or double, both fold to 100)
        assert primary == 100.0
        assert "100.0" in reason

    def test_fast_tempo_halves(self):
        """Test that fast tempos prefer the halved variant."""
        primary, half, double, reason = select_tempo_with_folding(200.0)

        # Should prefer 100 BPM (which could be base folded or half, both fold to 100)
        assert primary == 100.0
        assert "100.0" in reason

    def test_none_tempo(self):
        """Test handling of None tempo."""
        primary, half, double, reason = select_tempo_with_folding(None)

        assert primary is None
        assert half is None
        assert double is None
        assert reason == "no_tempo"

    def test_zero_tempo(self):
        """Test handling of zero tempo."""
        primary, half, double, reason = select_tempo_with_folding(0.0)

        assert primary is None
        assert reason == "no_tempo"

    def test_negative_tempo(self):
        """Test handling of negative tempo."""
        primary, half, double, reason = select_tempo_with_folding(-120.0)

        assert primary is None
        assert reason == "no_tempo"


class TestEstimateTempoWithFolding:
    """Tests for estimate_tempo_with_folding function."""

    def test_normal_signal(self):
        """Test tempo estimation with folding for a normal signal."""
        # Create a signal with some structure
        sr = 44100
        duration = 5  # seconds
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        primary, half, double, reason = estimate_tempo_with_folding(signal, sr)

        # Should return valid tempo or None
        assert primary is None or (30.0 <= primary <= 300.0)
        if primary is not None:
            # Note: half and double are based on the original base_tempo, not the folded primary
            assert isinstance(half, float)
            assert isinstance(double, float)
            assert isinstance(reason, str)

    def test_empty_signal(self):
        """Test handling of empty signal."""
        signal = np.array([], dtype=np.float32)

        primary, half, double, reason = estimate_tempo_with_folding(signal, sr=44100)

        assert reason == "librosa_unavailable_or_empty_audio"

    def test_none_signal(self):
        """Test handling of None signal."""
        primary, half, double, reason = estimate_tempo_with_folding(None, sr=44100)

        assert reason == "librosa_unavailable_or_empty_audio"

    def test_very_short_signal_gets_padded(self):
        """Test that very short signals are padded before estimation."""
        # Create a signal shorter than the padding threshold
        signal = np.random.randn(512).astype(np.float32) * 0.3

        primary, half, double, reason = estimate_tempo_with_folding(signal, sr=44100)

        # Should handle padding and return some result
        assert isinstance(reason, str)


class TestComputeTempoConfidence:
    """Tests for compute_tempo_confidence function."""

    def test_normal_signal_with_tempo(self):
        """Test confidence computation for a normal signal with estimated tempo."""
        # Create a signal with some rhythmic structure
        sr = 44100
        duration = 5  # seconds
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        score, label = compute_tempo_confidence(signal, sr, tempo_primary=120.0)

        assert 0.0 <= score <= 1.0
        assert label in ("low", "med", "high")

    def test_none_tempo(self):
        """Test handling of None tempo."""
        signal = np.random.randn(44100).astype(np.float32) * 0.3

        score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=None)

        assert score == 0.2
        assert label == "low"

    def test_zero_tempo(self):
        """Test handling of zero tempo."""
        signal = np.random.randn(44100).astype(np.float32) * 0.3

        score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=0.0)

        assert score == 0.2
        assert label == "low"

    def test_negative_tempo(self):
        """Test handling of negative tempo."""
        signal = np.random.randn(44100).astype(np.float32) * 0.3

        score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=-120.0)

        assert score == 0.2
        assert label == "low"

    def test_empty_signal(self):
        """Test handling of empty signal."""
        signal = np.array([], dtype=np.float32)

        score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=120.0)

        assert score == 0.2
        assert label == "low"

    def test_none_signal(self):
        """Test handling of None signal."""
        score, label = compute_tempo_confidence(None, sr=44100, tempo_primary=120.0)

        assert score == 0.2
        assert label == "low"

    def test_very_short_signal_gets_padded(self):
        """Test that very short signals are padded before analysis."""
        signal = np.random.randn(512).astype(np.float32) * 0.3

        score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=120.0)

        # Should handle padding and return valid result
        assert 0.0 <= score <= 1.0
        assert label in ("low", "med", "high")

    def test_confidence_labels(self):
        """Test that confidence labels match score ranges."""
        signal = np.random.randn(44100 * 5).astype(np.float32) * 0.3

        # Test multiple times to cover different scenarios
        for _ in range(3):
            score, label = compute_tempo_confidence(signal, sr=44100, tempo_primary=120.0)

            if score >= 0.66:
                assert label == "high"
            elif score >= 0.33:
                assert label == "med"
            else:
                assert label == "low"


class TestEndToEndWorkflow:
    """Integration tests for the complete tempo estimation workflow."""

    def test_full_tempo_workflow(self):
        """Test complete workflow: estimate tempo and compute confidence."""
        # Create a signal with some structure
        sr = 44100
        duration = 5  # seconds
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        # Estimate tempo
        primary, half, double, reason = estimate_tempo_with_folding(signal, sr)

        # If we got a tempo, compute confidence
        if primary is not None:
            score, label = compute_tempo_confidence(signal, sr, tempo_primary=primary)

            # Verify results are valid
            assert 30.0 <= primary <= 300.0
            assert half == primary / 2.0
            assert double == primary * 2.0
            assert 0.0 <= score <= 1.0
            assert label in ("low", "med", "high")

    def test_workflow_with_none_signal(self):
        """Test complete workflow with None signal."""
        # Estimate tempo
        primary, half, double, reason = estimate_tempo_with_folding(None, sr=44100)

        assert primary is None
        assert reason == "librosa_unavailable_or_empty_audio"

        # Compute confidence with None signal
        score, label = compute_tempo_confidence(None, sr=44100, tempo_primary=None)

        assert score == 0.2
        assert label == "low"
